import os
import environ
import numpy as np

import tensorflow as tf
from multiprocessing.pool import ThreadPool


class Detector:
    def __init__(self):
        self.graph_path = self._get_grap_paht()
        self.labels = ['noncrosswalk', 'crosswalk']
        self.sess = tf.Session()
        self._load_graph()

    def _get_grap_paht(self):
        directory = os.path.dirname(os.path.realpath(__file__))
        cwenv = environ.Env(GRAPH_PATH=(str, directory + '/output_graph_crosswalks.pb'))
        root = environ.Path(os.getcwd())
        environ.Env.read_env(root('.env'))
        return cwenv('GRAPH_PATH')

    def _load_graph(self):
        with tf.device("/cpu:0"):
            with tf.gfile.FastGFile(self.graph_path, 'rb') as f:
                graph_def = tf.GraphDef()
                graph_def.ParseFromString(f.read())
                _ = tf.import_graph_def(graph_def, name='')

    def detect(self, image):
        image_array = self._pil_to_tf(image)
        with tf.device("/gpu:0"):
            softmax_tensor = self.sess.graph.get_tensor_by_name('final_result:0')
            predictions = self.sess.run(softmax_tensor, {'DecodeJpeg:0': image_array})
            predictions = np.squeeze(predictions)
            answer = {}
            for node_id in range(len(predictions)):
                answer[self.labels[node_id]] = predictions[node_id]
            return answer

    def detect_multiple(self, images):
        image_array_list = [self._pil_to_tf(image) for image in images]

        pool = ThreadPool()

        with tf.device("/gpu:0"):
            softmax_tensor = self.sess.graph.get_tensor_by_name('final_result:0')
            threads = [pool.apply_async(operation, args=(self.sess, softmax_tensor, image,)) for image in
                       image_array_list]
            results = []
            for x in threads:
                results.append(x.get())

            return results

    @staticmethod
    def _pil_to_tf(image):
        return np.array(image)[:, :, 0:3]


def operation(sess, softmax, image):
    prediction = sess.run(softmax, {'DecodeJpeg:0': image})
    return prediction
