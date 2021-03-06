import sys
sys.path.append(r"D:\\ME-master\\ME-master")

import tensorflow as tf
import pickle
from sklearn.model_selection import train_test_split
import keras, keras.layers as L, keras.backend as K
from keras.callbacks import EarlyStopping
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import os
import astropy.io.fits as fits

import ME

def reset_tf_session():
    K.clear_session()
    tf.reset_default_graph()
    s = K.get_session()
    return s

with open('database248832.pkl', 'rb') as handle:
    b = pickle.load(handle)
    
profiles = b['Profiles']    
    
def plot_spectrum(profile):
  
    plt.title('sample spectrum')
  
    
    for i in range(4):
        plt.subplot(2,2,i+1)
        plt.plot(profile[i*56:(i+1)*56])
        
plot_spectrum(profiles[12487,:])  
plt.show()

def build_pca_autoencoder(spectrum_shape, code_size):
    """
    Here we define a simple linear autoencoder as described above.
    We also flatten and un-flatten data to be compatible with image shapes
    """
    
    encoder = keras.models.Sequential()
    encoder.add(L.InputLayer((spectrum_shape,)))
    #encoder.add(L.Flatten())                  #flatten image to vector
    encoder.add(L.Dense(code_size))           #actual encoder

    decoder = keras.models.Sequential()
    decoder.add(L.InputLayer((code_size,)))
    decoder.add(L.Dense(spectrum_shape))  #actual decoder, height*width*3 units
    
    return encoder,decoder

def generate_profiles(line_vector, flags, spaces, argument):
    param_vector = np.empty(len(flags))
    for j in range(len(flags)):
        if (flags[j]):
            param_vector[j] = spaces[1][j] + (spaces[2][j] - spaces[1][j])*np.random.random()
        else:
            param_vector[j] = spaces[0][j]
    profile = ME.ME_ff(line_vector, param_vector, argument)
    
    weights = np.concatenate( (np.full(56, 1), np.full(56*3,3))  )
    
    return (np.reshape(profile.T, (1, 56*4))*weights)
      
spectrum_shape  = 56*4

#s = reset_tf_session()
encoder, decoder = build_pca_autoencoder(spectrum_shape, code_size=10)

print(encoder.summary())
print(decoder.summary())

weights = np.concatenate( (np.full(56, 1), np.full(56*3,3))  )

X_train, X_test = train_test_split(profiles*weights, test_size=0.1, random_state=42)


es = EarlyStopping(monitor='val_loss', patience = 5, verbose=1)
inp = L.Input((spectrum_shape,))
code = encoder(inp)
reconstruction = decoder(code)
autoencoder = keras.models.Model(inputs=inp, outputs=reconstruction)

autoencoder.compile(optimizer='adamax', loss='mse')

history = autoencoder.fit(x=X_train, y=X_train, epochs=40,

                validation_data=[X_test, X_test], callbacks=[es],

                verbose=1)


plt.plot(history.history['loss'], label='train')
plt.plot(history.history['val_loss'], label='test')
plt.legend()

def visualize(profile,encoder,decoder):
    """Draws original, encoded and decoded spectrum"""
    code = encoder.predict(profile[None]) # img[None] is the same as img[np.newaxis, :]
    reco = reco = decoder.predict(code)
    
    plt.figure(figsize = (12,5))
    plt.subplot(2,1,1)
    plt.title("Original")
    plt.plot(profile)
    plt.plot(reco.flatten())

    
    plt.subplot(2,1,2)
    plt.title("Reconstructed")
    plt.plot(reco.flatten())
    plt.show()
    
    plot_spectrum(profile)  
    plot_spectrum(reco.flatten())  
    plt.show()
    
visualize(profiles[31482,:],encoder,decoder)

def check_real(x_c, y_c):
    directory = 'D:\\fits\\hao\\web\\csac.hao.ucar.edu\\data\\hinode\\sot\\level1\\2017\\09\\05\\SP3D\\20170905_030404\\'
    files_list = os.listdir(directory)
    spectra_file = fits.open(directory + files_list[x_c])
    real_I = spectra_file[0].data[0][y_c][56:].astype('float64')*2
    real_Q = spectra_file[0].data[1][y_c][56:].astype('float64')*3
    real_U = spectra_file[0].data[2][y_c][56:].astype('float64')*3
    real_V = spectra_file[0].data[3][y_c][56:].astype('float64')*3
            
    a = 0.5/(np.max(real_I) - np.min(real_I))
    b = 0.5*(np.max(real_I) - 2*np.min(real_I))/(np.max(real_I) - np.min(real_I))
            
    real_I = a*(real_I) + b
    real_Q = a*real_Q
    real_U = a*real_U
    real_V = a*real_V
            
    real_sp = np.concatenate((real_I, real_Q, real_U, real_V))
    visualize(real_sp,encoder,decoder)
    