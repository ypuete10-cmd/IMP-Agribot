import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_keras_model(
    tf.keras.models.load_model("plant_health.keras"))
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_types = [tf.float16]

tflite_model = converter.convert()
with open("plant_health.tflite", "wb") as f:
    f.write(tflite_model)
print(f"TFLite size: {len(tflite_model)/1024:.0f} KB")