import tensorflow as tf
import numpy as np
import json, sys

interp = tf.lite.Interpreter(model_path="plant_health.tflite")
interp.allocate_tensors()
inp = interp.get_input_details()[0]

class_names = json.load(open("class_names.json"))

img_path = sys.argv[1] if len(sys.argv) > 1 else "test_leaf.jpg"
img = tf.keras.utils.load_img(img_path, target_size=(224, 224))
img = tf.keras.utils.img_to_array(img)
img = np.expand_dims(img.astype(np.float32), 0)

interp.set_tensor(inp["index"], img)
interp.invoke()
pred = interp.get_tensor(interp.get_output_details()[0]["index"])[0]

for i in np.argsort(pred)[-3:][::-1]:
    print(f"{class_names[i]}: {pred[i]*100:.1f}%")