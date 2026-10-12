"""Untrained CT slice-classification baseline architecture."""
import torch
from torch import nn

class HemorrhageCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers=nn.Sequential(nn.Conv2d(3,16,5,stride=2,padding=2),nn.GroupNorm(4,16),nn.ReLU(),
            nn.Conv2d(16,32,3,stride=2,padding=1),nn.GroupNorm(4,32),nn.ReLU(),
            nn.Conv2d(32,64,3,stride=2,padding=1),nn.GroupNorm(8,64),nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),nn.Flatten(),nn.Linear(64,6))
    def forward(self,x):
        if x.ndim!=4 or x.shape[1]!=3:raise ValueError('Three CT window channels required')
        return self.layers(x)
