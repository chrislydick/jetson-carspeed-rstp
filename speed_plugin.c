#include <gst/gst.h>
#include <gst/base/gstbasetransform.h>
#include <nvds_meta.h>
#include <nvds_meta_schema.h>
#include <sqlite3.h>
#include <math.h>

GST_DEBUG_CATEGORY_STATIC(gst_speed_debug);
#define GST_CAT_DEFAULT gst_speed_debug

typedef struct {
  gdouble x;
  gdouble y;
  gdouble ts;
} HistoryPoint;

typedef struct {
  gint cap;
  gint count;
  gint idx;
  HistoryPoint *pts;
} History;

static History *history_new(gint cap) {
  History *h = g_new0(History, 1);
  h->cap = cap;
  h->count = 0;
  h->idx = 0;
  h->pts = g_new0(HistoryPoint, cap);
  return h;
}

static void history_free(gpointer data) {
  History *h = (History *)data;
  g_free(h->pts);
  g_free(h);
}

static void history_add(History *h, gdouble x, gdouble y, gdouble ts) {
  h->pts[h->idx].x = x;
  h->pts[h->idx].y = y;
  h->pts[h->idx].ts = ts;
  h->idx = (h->idx + 1) % h->cap;
  if (h->count < h->cap)
    h->count++;
}

static gdouble history_speed(const History *h, gdouble ppm) {
  if (h->count < 2)
    return 0.0;
  gdouble sum_t = 0.0, sum_x = 0.0, sum_y = 0.0;
  for (int i = 0; i < h->count; i++) {
    int idx = (h->idx - h->count + i + h->cap) % h->cap;
    sum_t += h->pts[idx].ts;
    sum_x += h->pts[idx].x;
    sum_y += h->pts[idx].y;
  }
  gdouble mean_t = sum_t / h->count;
  gdouble mean_x = sum_x / h->count;
  gdouble mean_y = sum_y / h->count;
  gdouble num_x = 0.0, num_y = 0.0, den = 0.0;
  for (int i = 0; i < h->count; i++) {
    int idx = (h->idx - h->count + i + h->cap) % h->cap;
    gdouble dt = h->pts[idx].ts - mean_t;
    num_x += dt * (h->pts[idx].x - mean_x);
    num_y += dt * (h->pts[idx].y - mean_y);
    den += dt * dt;
  }
  if (den == 0.0)
    return 0.0;
  gdouble vx = num_x / den;
  gdouble vy = num_y / den;
  return sqrt(vx * vx + vy * vy) / ppm;
}

typedef struct {
  GstBaseTransform parent;
  gfloat ppm;
  gchar *db_path;
  sqlite3 *db;
  gint window;
  GHashTable *history; /* key: guint64 track id, value: History* */
  gdouble H[9];
  gboolean have_h;
  GString *sql_batch;
} GstSpeed;

G_DEFINE_TYPE(GstSpeed, gst_speed, GST_TYPE_BASE_TRANSFORM);

enum { PROP_0, PROP_PPM, PROP_DB, PROP_HOMOGRAPHY, PROP_WINDOW };

static void gst_speed_set_property(GObject *object, guint prop_id,
                                   const GValue *value, GParamSpec *pspec) {
  GstSpeed *speed = (GstSpeed *)object;
  switch (prop_id) {
  case PROP_PPM:
    speed->ppm = g_value_get_float(value);
    break;
  case PROP_DB:
    g_free(speed->db_path);
    speed->db_path = g_value_dup_string(value);
    break;
  case PROP_HOMOGRAPHY: {
    const gchar *s = g_value_get_string(value);
    speed->have_h = FALSE;
    if (s && *s) {
      gchar **tokens = g_strsplit_set(s, ",; ", -1);
      int i;
      for (i = 0; tokens[i] && i < 9; i++)
        speed->H[i] = g_ascii_strtod(tokens[i], NULL);
      speed->have_h = (i == 9);
      g_strfreev(tokens);
    }
    break;
  }
  case PROP_WINDOW:
    speed->window = g_value_get_int(value);
    if (speed->window < 2)
      speed->window = 2;
    break;
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID(object, prop_id, pspec);
  }
}

static void gst_speed_get_property(GObject *object, guint prop_id, GValue *value,
                                   GParamSpec *pspec) {
  GstSpeed *speed = (GstSpeed *)object;
  switch (prop_id) {
  case PROP_PPM:
    g_value_set_float(value, speed->ppm);
    break;
  case PROP_DB:
    g_value_set_string(value, speed->db_path);
    break;
  case PROP_HOMOGRAPHY: {
    if (speed->have_h) {
      gchar *str = g_strdup_printf(
          "%f,%f,%f,%f,%f,%f,%f,%f,%f",
          speed->H[0], speed->H[1], speed->H[2],
          speed->H[3], speed->H[4], speed->H[5],
          speed->H[6], speed->H[7], speed->H[8]);
      g_value_take_string(value, str);
    } else {
      g_value_set_string(value, "");
    }
    break;
  }
  case PROP_WINDOW:
    g_value_set_int(value, speed->window);
    break;
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID(object, prop_id, pspec);
  }
}

static void gst_speed_finalize(GObject *obj) {
  GstSpeed *speed = (GstSpeed *)obj;
  if (speed->db)
    sqlite3_close(speed->db);
  g_free(speed->db_path);
  if (speed->history)
    g_hash_table_unref(speed->history);
  if (speed->sql_batch)
    g_string_free(speed->sql_batch, TRUE);
  G_OBJECT_CLASS(gst_speed_parent_class)->finalize(obj);
}

static gboolean gst_speed_start(GstBaseTransform *trans) {
  GstSpeed *speed = (GstSpeed *)trans;
  if (sqlite3_open(speed->db_path, &speed->db) != SQLITE_OK) {
    g_printerr("Could not open DB %s\n", speed->db_path);
    GST_DEBUG_OBJECT(speed, "failed to open DB %s", speed->db_path);
    speed->db = NULL;
  } else {
    sqlite3_exec(speed->db,
                 "CREATE TABLE IF NOT EXISTS vehicles (timestamp REAL, track_id INTEGER, speed REAL);",
                 NULL, NULL, NULL);
    speed->sql_batch = g_string_new(NULL);
    GST_DEBUG_OBJECT(speed, "opened DB %s", speed->db_path);
  }
  speed->history = g_hash_table_new_full(g_int64_hash, g_int64_equal, NULL,
                                         history_free);
  return TRUE;
}

static GstFlowReturn gst_speed_transform_ip(GstBaseTransform *trans, GstBuffer *buf) {
  GstSpeed *speed = (GstSpeed *)trans;
  NvDsBatchMeta *batch = gst_buffer_get_nvds_batch_meta(buf);
  if (!batch || !speed->db)
    return GST_FLOW_OK;
  for (NvDsMetaList *l = batch->frame_meta_list; l; l = l->next) {
    NvDsFrameMeta *frame = (NvDsFrameMeta *)l->data;
    gdouble ts = frame->ntp_timestamp / 1e9;
    g_string_truncate(speed->sql_batch, 0);
    for (NvDsMetaList *o = frame->obj_meta_list; o; o = o->next) {
      NvDsObjectMeta *obj = (NvDsObjectMeta *)o->data;
      guint64 tid = obj->object_id;
      gdouble cx = obj->rect_params.left + obj->rect_params.width / 2.0;
      gdouble cy = obj->rect_params.top + obj->rect_params.height / 2.0;
      if (speed->have_h) {
        gdouble tx = speed->H[0] * cx + speed->H[1] * cy + speed->H[2];
        gdouble ty = speed->H[3] * cx + speed->H[4] * cy + speed->H[5];
        gdouble tz = speed->H[6] * cx + speed->H[7] * cy + speed->H[8];
        if (tz != 0) {
          cx = tx / tz;
          cy = ty / tz;
        }
      }
      History *hist = g_hash_table_lookup(speed->history, GUINT_TO_POINTER(tid));
      if (!hist) {
        hist = history_new(speed->window);
        g_hash_table_insert(speed->history, GUINT_TO_POINTER(tid), hist);
      }
      history_add(hist, cx, cy, ts);
      gdouble spd = history_speed(hist, speed->ppm);
      if (spd > 0) {
        char *sql = sqlite3_mprintf("INSERT INTO vehicles(timestamp, track_id, speed) VALUES(%f,%llu,%f);", ts, (unsigned long long)tid, spd);
        g_string_append(speed->sql_batch, sql);
        sqlite3_free(sql);
      }
    }
    if (speed->sql_batch->len > 0) {
      sqlite3_exec(speed->db, speed->sql_batch->str, NULL, NULL, NULL);
      GST_DEBUG_OBJECT(speed, "executed SQL batch: %s", speed->sql_batch->str);
    }
  }
  return GST_FLOW_OK;
}

static void gst_speed_class_init(GstSpeedClass *klass) {
  GstElementClass *element_class = GST_ELEMENT_CLASS(klass);
  gst_element_class_set_static_metadata(element_class, "Speed Estimator", "Filter/Analysis", "Estimate object speed", "openai");
  GstBaseTransformClass *trans = GST_BASE_TRANSFORM_CLASS(klass);
  trans->start = gst_speed_start;
  trans->transform_ip = gst_speed_transform_ip;
  GObjectClass *gobject_class = G_OBJECT_CLASS(klass);
  gobject_class->finalize = gst_speed_finalize;
  gobject_class->set_property = gst_speed_set_property;
  gobject_class->get_property = gst_speed_get_property;

  g_object_class_install_property(gobject_class, PROP_PPM,
      g_param_spec_float("ppm", "Pixels per meter", "Scaling for speed", 0.1, 1000.0, 20.0, G_PARAM_READWRITE));
  g_object_class_install_property(gobject_class, PROP_DB,
      g_param_spec_string("db", "Database path", "SQLite DB path", "vehicles.db", G_PARAM_READWRITE));
  g_object_class_install_property(gobject_class, PROP_HOMOGRAPHY,
      g_param_spec_string("homography", "3x3 homography", "Row-major matrix", "", G_PARAM_READWRITE));
  g_object_class_install_property(gobject_class, PROP_WINDOW,
      g_param_spec_int("window", "History window", "Number of observations", 2, 60,
                       3, G_PARAM_READWRITE));
}

static void gst_speed_init(GstSpeed *speed) {
  speed->ppm = 20.0;
  speed->db_path = g_strdup("vehicles.db");
  speed->have_h = FALSE;
  speed->window = 3;
  speed->history = NULL;
  speed->sql_batch = NULL;
  for (int i = 0; i < 9; i++)
    speed->H[i] = (i % 4 == 0) ? 1.0 : 0.0; /* identity */
}

static gboolean plugin_init(GstPlugin *plugin) {
  GST_DEBUG_CATEGORY_INIT(gst_speed_debug, "speedtrack", 0, "speedtrack plugin");
  return gst_element_register(plugin, "speedtrack", GST_RANK_NONE, gst_speed_get_type());
}

GST_PLUGIN_DEFINE(GST_VERSION_MAJOR, GST_VERSION_MINOR, speedtrack, "Speed estimator", plugin_init, "1.0", "LGPL", "deepstream-speed", "")
