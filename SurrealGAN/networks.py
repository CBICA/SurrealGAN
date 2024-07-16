import torch
import torch.nn as nn
import torch.nn.functional as F

from .modules import Sub_Adder, TwoInputSequential

__author__ = "Zhijian Yang"
__copyright__ = "Copyright 2019-2020 The CBICA & SBIA Lab"
__credits__ = ["Zhijian Yang"]
__license__ = "See LICENSE file"
__version__ = "0.1.0"
__maintainer__ = "Zhijian Yang"
__email__ = "zhijianyang@outlook.com"
__status__ = "Development"


###############################################################################
# Functions
###############################################################################


def weights_init(m):  # type: ignore
    classname = m.__class__.__name__
    if classname.find("Linear") != -1:
        m.weight.data.normal_(0, 0.1)


def define_Linear_Mapping(nROI, nPattern):  # type: ignore
    netG = LMappingGenerator(nPattern, nROI)
    netG.apply(weights_init)
    return netG


def define_Linear_Discriminator(nROI):  # type: ignore
    netD = LDiscriminator(nROI)
    netD.apply(weights_init)
    return netD


def define_Linear_Reconstruction(nROI, nPattern):  # type: ignore
    netC = LEncoder(nPattern, nROI)
    netC.apply(weights_init)
    return netC


def define_Linear_Decomposer(nROI, nPattern):  # type: ignore
    netD = LDecompose(nPattern, nROI)
    netD.apply(weights_init)
    return netD


def define_Latent_Corr(ndim):  # type: ignore
    netL = LLatentCorr(ndim)
    netL.apply(weights_init)
    return netL


##############################################################################
# Network Classes
##############################################################################


class LMappingGenerator(nn.Module):
    def __init__(self, nPattern, nROI, product_layer=Sub_Adder):  # type: ignore
        super(LMappingGenerator, self).__init__()
        model = []

        def block(in_layer, out_layer, normalize=False):  # type: ignore
            layers = [nn.Linear(in_layer, out_layer, bias=False)]
            if normalize:
                layers.append(nn.BatchNorm1d(out_layer, 0.8))
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            return layers

        model += block(nROI, int(nROI / 2)) + block(int(nROI / 2), int(nROI / 4))
        model.append(product_layer(int(nROI / 4), nPattern))
        model += block(int(nROI / 4), int(nROI / 2)) + block(int(nROI / 2), nROI)
        # model.append(nn.Linear(nROI, nROI,bias=False))
        self.model = TwoInputSequential(*model)

    def forward(self, input_x, input_z):  # type: ignore
        return self.model(input_x, input_z)


class LEncoder(nn.Module):
    def __init__(self, nPattern, nROI):  # type: ignore
        super(LEncoder, self).__init__()
        model = []
        self.nPattern = nPattern

        def block(in_layer, out_layer, normalize=True):  # type: ignore
            layers = []
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            layers.append(nn.Linear(in_layer, out_layer))
            return layers

        model.append(nn.Linear(nROI, int(nROI / 2)))
        model += block(int(nROI / 2), int(nROI / 4)) + block(int(nROI / 4), nPattern)
        self.model = nn.Sequential(*model)

    def forward(self, input_y):  # type: ignore
        zt = self.model(input_y)
        return zt


class LDecompose(nn.Module):
    def __init__(self, nPattern, nROI):  # type: ignore
        super(LDecompose, self).__init__()
        model = []
        self.nPattern = nPattern
        self.nROI = nROI

        def block(in_layer, out_layer):  # type: ignore
            layers = []
            layers.append(nn.LeakyReLU(0.2, inplace=False))
            layers.append(nn.Linear(in_layer, out_layer))
            return layers

        model += block(int(nROI), int(nPattern * nROI))
        self.model = nn.Sequential(*model)

    def forward(self, input_y):  # type: ignore
        z_decompose = self.model(input_y)
        return [
            z_decompose[:, self.nROI * i : self.nROI * (i + 1)]
            for i in range(self.nPattern)
        ]


class LDiscriminator(nn.Module):
    def __init__(self, nROI):  # type: ignore
        super(LDiscriminator, self).__init__()
        self.model = nn.Sequential(
            nn.Linear(nROI, int(nROI / 2), bias=True),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(int(nROI / 2), int(nROI / 4), bias=True),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(int(nROI / 4), 2, bias=True),
        )

    def forward(self, input_y):  # type: ignore
        pred = self.model(input_y)
        return pred


class LLatentCorr(nn.Module):
    def __init__(self, ndim):  # type: ignore
        super(LLatentCorr, self).__init__()
        self.model = nn.Sequential(
            nn.Linear(1, ndim, bias=False),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(ndim, ndim, bias=False),
        )

    def forward(self):  # type: ignore
        pred = F.tanh(self.model(nn.Parameter(torch.tensor([1.0]))))
        return pred
