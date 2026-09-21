import tensorflow as tf
from tensorflow.keras import layers, models
import json

# ---------- Config ----------
IMG_SIZE = 224
BATCH = 32
EPOCHS = 10
DATA_DIR = "C:/Users/yvett/plantvillage_subset"
# ----------------------------

train_ds = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR, validation_split=0.2, subset="training",
    seed=42, image_size=(IMG_SIZE, IMG_SIZE), batch_size=BATCH)
val_ds = tf.keras.utils.image_dataset_from_directory(
    DATA_DIR, validation_split=0.2, subset="validation",
    seed=42, image_size=(IMG_SIZE, IMG_SIZE), batch_size=BATCH)

class_names = train_ds.class_names
print(f"{len(class_names)} classes: {class_names}")

AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(AUTOTUNE)
val_ds = val_ds.cache().prefetch(AUTOTUNE)

augment = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.15),
    layers.RandomZoom(0.1),
    layers.RandomContrast(0.1),
])

base = tf.keras.applications.MobileNetV3Small(
    input_shape=(IMG_SIZE, IMG_SIZE, 3),
    include_top=False, weights="imagenet")
base.trainable = False

inputs = layers.Input((IMG_SIZE, IMG_SIZE, 3))
x = augment(inputs)
x = tf.keras.applications.mobilenet_v3.preprocess_input(x)
x = base(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.3)(x)
outputs = layers.Dense(len(class_names), activation="softmax")(x)
model = models.Model(inputs, outputs)

model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
              loss="sparse_categorical_crossentropy",
              metrics=["accuracy"])

model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS)

# Fine-tune last 30 layers
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False
model.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
              loss="sparse_categorical_crossentropy",
              metrics=["accuracy"])
model.fit(train_ds, validation_data=val_ds, epochs=5)

model.save("plant_health.keras")
with open("class_names.json", "w") as f:
    json.dump(class_names, f)
print("Saved plant_health.keras + class_names.json")