# this file shows how to use `nn_config` to build a model consisting of multiple back to back layers
# We build a CNN->LSTM model consisting of 3 CNN layers followed by max pooling and then feeding its output
# to two LSTM layers.

from AI4Water import Model
from AI4Water.utils.datasets import arg_beach

df = arg_beach()
input_features = list(df.columns)[0:-1]

# column in dataframe to bse used as output/target
outputs = list(df.columns)[-1]

sub_sequences = 3
lookback = 15
time_steps = lookback // sub_sequences
layers = {
    "Input": {'config': {'shape': (sub_sequences, time_steps, len(input_features))}},
    "TimeDistributed_0": {'config': {'name': 'td_for_conv1'}},
    'conv1d_0': {'config':  {'filters': 64, 'kernel_size': 2, 'name': 'first_conv1d'}},
    'LeakyRelu_0': {'config':  {}},
    "TimeDistributed_1": {'config':  {}},
    'conv1d_1': {'config':  {'filters': 32, 'kernel_size': 2}},
    'elu_1': {'config':  {}},
    "TimeDistributed_2": {'config':  {}},
    'conv1d_2': {'config':  {'filters': 16, 'kernel_size': 2}},
    'tanh_2': {'config':  {}},
    "TimeDistributed_3": {'config':  {}},
    "maxpool1d": {'config':  {'pool_size': 2}},
    "TimeDistributed_4": {'config':  {}},
    'flatten': {'config':  {}},
    'lstm_0': {'config': {'units': 64, 'activation': 'relu', 'dropout': 0.4, 'recurrent_dropout': 0.5,
                          'return_sequences': True,
               'name': 'lstm_0'}},
    'Relu_1': {'config':  {}},
    'lstm_1': {'config': {'units': 32, 'activation': 'relu', 'dropout': 0.4, 'recurrent_dropout': 0.5,
                          'name': 'lstm_1'}},
    'sigmoid_2': {'config':  {}},
    'Dense': {'config':  {'units': 1}}
}

model = Model(
    data=df,
    batch_size=16,
    lookback=lookback,
    inputs=input_features,
    outputs=outputs,
    model={'layers':layers},
    lr=0.0001
              )

# This model is built only to showcase how to build multi layer model by manipulating config
# history = model.fit(indices='random')

#y, obs = model.predict(st=0, use_datetime_index=False, marker='.', linestyle='')
