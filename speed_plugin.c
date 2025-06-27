#include <gst/gst.h>
#include <gst/base/gstbasetransform.h>
#include <nvds_meta.h>
#include <nvds_meta_schema.h>
#include <sqlite3.h>
#include <math.h>

typedef struct {
  GstBaseTransform parent;
  gfloat ppm;
  gchar *db_path;
  sqlite3 *db;
  GHashTable *prev; /* key: guint64 track id, value: gdouble[3] {x, y, ts} */
} GstSpeed;

G_DEFINE_TYPE(GstSpeed, gst_speed, GST_TYPE_BASE_TRANSFORM);

enum { PROP_0, PROP_PPM, PROP_DB };

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
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID(object, prop_id, pspec);
  }
}

static void gst_speed_finalize(GObject *obj) {
  GstSpeed *speed = (GstSpeed *)obj;
  if (speed->db) sqlite3_close(speed->db);
  g_free(speed->db_path);
  if (speed->prev) g_hash_table_unref(speed->prev);
  G_OBJECT_CLASS(gst_speed_parent_class)->finalize(obj);
}

static gboolean gst_speed_start(GstBaseTransform *trans) {
  GstSpeed *speed = (GstSpeed *)trans;
  if (sqlite3_open(speed->db_path, &speed->db) != SQLITE_OK) {
    g_printerr("Could not open DB %s\n", speed->db_path);
    speed->db = NULL;
  } else {
    sqlite3_exec(speed->db,
                 "CREATE TABLE IF NOT EXISTS vehicles (timestamp REAL, track_id INTEGER, speed REAL);",
                 NULL, NULL, NULL);
  }
  speed->prev = g_hash_table_new_full(g_int64_hash, g_int64_equal, NULL, g_free);
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
    for (NvDsMetaList *o = frame->obj_meta_list; o; o = o->next) {
      NvDsObjectMeta *obj = (NvDsObjectMeta *)o->data;
      guint64 tid = obj->object_id;
      gdouble cx = obj->rect_params.left + obj->rect_params.width / 2.0;
      gdouble cy = obj->rect_params.top + obj->rect_params.height / 2.0;
      gdouble *prev = g_hash_table_lookup(speed->prev, GUINT_TO_POINTER(tid));
      gdouble spd = 0.0;
      if (prev) {
        gdouble dist = hypot(cx - prev[0], cy - prev[1]);
        gdouble dt = ts - prev[2];
        if (dt > 0)
          spd = (dist / speed->ppm) / dt;
        prev[0] = cx;
        prev[1] = cy;
        prev[2] = ts;
      } else {
        gdouble *vals = g_new(gdouble, 3);
        vals[0] = cx;
        vals[1] = cy;
        vals[2] = ts;
        g_hash_table_insert(speed->prev, GUINT_TO_POINTER(tid), vals);
      }
      if (spd > 0) {
        char *sql = sqlite3_mprintf("INSERT INTO vehicles(timestamp, track_id, speed) VALUES(%f,%llu,%f);", ts, (unsigned long long)tid, spd);
        sqlite3_exec(speed->db, sql, NULL, NULL, NULL);
        sqlite3_free(sql);
      }
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
}

static void gst_speed_init(GstSpeed *speed) {
  speed->ppm = 20.0;
  speed->db_path = g_strdup("vehicles.db");
}

static gboolean plugin_init(GstPlugin *plugin) {
  return gst_element_register(plugin, "speedtrack", GST_RANK_NONE, gst_speed_get_type());
}

GST_PLUGIN_DEFINE(GST_VERSION_MAJOR, GST_VERSION_MINOR, speedtrack, "Speed estimator", plugin_init, "1.0", "LGPL", "deepstream-speed", "")
