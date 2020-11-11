import numpy as np
import keras
import tensorflow as tf
import data_setup
from sklearn.metrics import accuracy_score

# Hyperparameters
batch_size = 32
t = 10  # a.k.a. num predictions


def train_model(model, x_train, y_train, x_val, y_val, epochs):
    with tf.device("gpu:0"):
        model.fit(x_train, y_train, batch_size=batch_size, epochs=epochs, verbose=1,
                  validation_data=(x_val, y_val))


# This function computes the accuracy and the uncertainty of a model wrt a set of samples
def evaluate_model(model, x, y, multiple_pred):
    num_predictions = t if multiple_pred else 1

    # predict real samples to compute 1. and 2.
    n_samples = x.shape[0]
    p_hat = np.zeros((num_predictions, n_samples, data_setup.num_classes))
    for i in range(num_predictions):
        p_hat[i] = model.predict(x)

    y_pred_mean, y_pred_uc = compute_pred_distribution(p_hat)

    y_pred = np.argmax(y_pred_mean, axis=1)  # extract class with highest score for each sample
    y_pred_one_hot = keras.utils.to_categorical(y_pred, data_setup.num_classes)
    acc = accuracy_score(y, y_pred_one_hot)

    uc = y_pred_uc[range(n_samples), y_pred]  # for each samples we consider the uncertainty of the predicted class
    uc = np.mean(uc)  # compute a single scalar for all samples
    return acc, uc


# y_true has shape (n_samples, n_classes)
# y_pred has shape (num_predictions, n_samples, n_classes)
# y_pred is the matrix of all T predictions for each sample
def compute_pred_distribution(y_pred):
    y_pred = np.transpose(y_pred, [1, 0, 2])  # change shape to (batch_size, num_predictions, num_classes)
    # 1. Compute mean
    y_pred_mean = np.mean(y_pred, axis=1)  # avg score for each class, with shape (n_samples, num_classes)
    # 1.1 Recompute softmax across each sample
    y_pred_mean = np.exp(y_pred_mean)
    y_pred_mean /= np.sum(y_pred_mean, axis=1, keepdims=True)

    # 2. Compute uncertainty
    epistemic = np.mean(y_pred ** 2, axis=1) - np.mean(y_pred, axis=1) ** 2
    aleatoric = np.mean(y_pred * (1 - y_pred), axis=1)
    y_pred_uc = epistemic + aleatoric  # with shape (n_samples, n_classes)
    return y_pred_mean, y_pred_uc  # each with shape (n_samples, n_classes)
