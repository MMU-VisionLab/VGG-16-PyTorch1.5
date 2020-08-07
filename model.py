'''
PyTorch implementation of VGG-16 architecture.
'''
import torch
import torch.nn as nn
from torch.optim import Adam, lr_scheduler
import cfg

class Model(nn.Module):
    '''
    VGG-16 model with batch normalization layers.
    '''

    def init_weights(self):
        '''
        Initialize the weight values for the neurons in the netowkr.
        '''

        #initialize the weights and bias for every layer depending on the type of layer.
        for mod in self.modules():

            if isinstance(mod, nn.Conv2d): #for convolutional layers.
                nn.init.kaiming_normal_(mod.weight, mode='fan_out', nonlinearity='relu')
                if mod.bias is not None: #if bias exists.
                    nn.init.constant_(mod.bias, 0.1)
            elif isinstance(mod, nn.BatchNorm2d):
                nn.init.constant_(mod.weight, 1)
                nn.init.constant_(mod.bias, 0.1)
            elif isinstance(mod, nn.Linear):
                nn.init.normal_(mod.weight, 0, 0.01)
                nn.init.constant_(mod.bias, 0.1)



    def __init__(self, resized_img_size=cfg.RESIZED_IMAGE_SIZE, num_classes=cfg.NUM_CLASSES, init_weights=True):
        '''
        Architecture initialization.
        '''
        super(Model, self).__init__()

        #convolutional layer configuration for VGG-16 network.
        #the values stands for the number of output filters in every layer of CNN while 'M' stands for Max-Pool layer.
        self.cfgs = {
            'conv':[64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M', 512, 512, 512, 'M', 512, 512, 512, 'M'],
            'fc':[1024, 1024, num_classes] #not recommended to have number of classes as the output channel size except the last layer.
        }

        conv_layers = []
        in_channels = 3 #the first input channel.

        #appends every convolutional layer in a list.
        for item in self.cfgs['conv']:

            if item == 'M':
                conv_layers += [nn.MaxPool2d(kernel_size=2, stride=2)] #maxpool layer
            else:
                #2D convolutional with kernel size of 3 for every layer.
                conv2d = nn.Conv2d(in_channels=in_channels, out_channels=item, kernel_size=3, padding=1)
                conv_layers += [conv2d, nn.BatchNorm2d(num_features=item), nn.ReLU(inplace=True)]
                in_channels = item #updates the input channel with the last output channel.

        #build convolutional layers of VGG-16 from the list.
        self.features = nn.Sequential(*conv_layers) #unpacks every layer from the list and place them in a sequence.
        self.avgpool = nn.AdaptiveAvgPool2d((7, 7))

        #we want to find the last output channel size of the convolutional layers.
        index = -1 #start from the final index
        while isinstance(self.cfgs['conv'][index], str): #repeats until the final index points to an integer value rather than a string.
            index -= 1

        num_pools = conv_layers.count('M') #get the number of pooling layers used.

        #when the last convolutional layer's output is flattened, the number of total input is defined by
        #(Last output channel num of the conv layer) x (pooled image size) x (pooled image size)
        #pooled image size can be calculated using the original image size divided by 2 raised to the power of (num of maxpools used)
        #NOTE that all these are assuming that the maxpools are of stride 2 and every convolutional layers are using zero-padding.
        fc_input_channel = self.cfgs['conv'][index] * 2 * resized_img_size//2**num_pools

        fc_layers = []

        #appends every fully-connected layers into the list. IF THERE ARE LAYERS WITH OUTPUT CHANNEL SIZE THE SAME AS NUM OF CLASS OTHER THAN THE FINAL LAYER, THE IF-ELSE LOGIC BELOW HAS TO BE MODIFIED!
        for item in self.cfgs['fc']:

            fully_connected_layer = nn.Linear(fc_input_channel, item)

            #except for the last layer of fully-connected, we want to have ReLU act func and dropout. (assuming on the last layer has the output cannel size as the class number)
            if not item == num_classes:
                fc_layers += [fully_connected_layer, nn.ReLU(inplace=True), nn.Dropout()]
            else:
                fc_layers += [fully_connected_layer] #the last layer does not consist of actv. func. nor dropout.

            fc_input_channel = item #updates the input channel to the last output chanell

        #build the fully-connected networks.
        self.classifier = nn.Sequential(*fc_layers)

        #initiliaze the weight parameters in the network.
        if init_weights:
            self.init_weights()

    def forward(self, input_x):
        '''
        Forward-propagation.
        '''
        hidden_x = self.features(input_x) #convolutional layers
        hidden_x = self.avgpool(hidden_x) #avgpool layer
        hidden_x = torch.flatten(hidden_x, 1) #flatten the output of conv layers.
        output = self.classifier(hidden_x) #fully-connected layers

        return output


#initialize the model
VGG = Model()


OPTIMIZER = Adam(VGG.parameters(), lr=cfg.LEARNING_RATE) #optimizer
LR_DECAY = lr_scheduler.ExponentialLR(OPTIMIZER, gamma=cfg.LR_DECAY_RATE) #scheduler is used to lower the learning rate during training later.
LOSS_CRITERION = nn.CrossEntropyLoss() #loss function.

VGG = VGG.to(cfg.DEVICE) #move the network to GPU if available.
