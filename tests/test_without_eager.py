import os
import unittest
import site  # so that AI4Water directory is in path
site.addsitedir(os.path.dirname(os.path.dirname(__file__)))

import tensorflow as tf

tf.compat.v1.disable_eager_execution()

from AI4Water.utils.datasets import load_nasdaq
from AI4Water import InputAttentionModel, DualAttentionModel


def make_and_run(input_model, _layers=None, lookback=12, epochs=1, **kwargs):

    df = load_nasdaq()

    model = input_model(
        data=df,
        verbosity=0,
        batch_size=64,
        lookback=lookback,
        lr=0.001,
        epochs=epochs,
        **kwargs
    )

    _ = model.fit(indices='random')

    _, pred_y = model.predict(use_datetime_index=False)

    return pred_y

class TestModels(unittest.TestCase):

    # InputAttention based model does not conform reproducibility so just testing that it runs.

    def test_InputAttentionModel(self):

        prediction = make_and_run(InputAttentionModel)
        self.assertGreater(float(prediction[0].sum()), 0.0)

    def test_DualAttentionModel(self):
        # DualAttentionModel based model

        prediction = make_and_run(DualAttentionModel)
        self.assertGreater(float(prediction[0].sum()), 0.0)


if __name__ == "__main__":
    unittest.main()