import os
import torch
from torch import nn
import torch.nn.functional as F
from torchvision.models import vgg16
import numpy as np
import matplotlib.pyplot as plt
import torchvision.transforms.functional as TF
import json
import imageio
import configargparse
from sklearn.preprocessing import StandardScaler

# configs
parser = configargparse.ArgumentParser()
parser.add_argument("--img_size", type=int, default=256,
                        help='image size')
parser.add_argument("--show_bg", action='store_true',
                        help='plot background features')
parser.add_argument('--gpu', type=int, default=7)
args = parser.parse_args()

os.environ["CUDA_VISIBLE_DEVICES"]= str(args.gpu)

def load_blender_data(basedir, size=-1, device='cuda:0'):
    splits = ['train', 'val', 'test']
    metas = {}
    for s in splits:
        with open(os.path.join(basedir, 'transforms_{}.json'.format(s)), 'r') as fp:
            metas[s] = json.load(fp)

    all_imgs = []
    counts = [0]
    for s in splits:
        meta = metas[s]
        imgs = []
        for frame in meta['frames'][::1]:
            fname = os.path.join(basedir, frame['file_path'] + '.png')
            imgs.append(imageio.imread(fname))
        imgs = (np.array(imgs) / 255.).astype(np.float32) # keep all 4 channels (RGBA)
        all_imgs.append(imgs)
    
    imgs = np.concatenate(all_imgs, 0)

    imgs = torch.from_numpy(imgs).to(device).permute([0,3,1,2])[:, :3, ...]
    if size > 0:
        imgs = TF.resize(imgs, size=size)
        
    return imgs

# load img
img_size = args.img_size
N_imgs = 10
img_dir = './data/nerf_synthetic/clevr_100_2objects'
device = 'cuda:0'
images = load_blender_data(img_dir, size=img_size)[:N_imgs]


# vgg process
vgg_features = vgg16(pretrained=True).features
feature_extractor = nn.Sequential()
for i in range(16):
    feature_extractor.add_module(str(i), vgg_features[i])
feature_extractor = feature_extractor.to(device)


x = TF.normalize(images, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
x = feature_extractor(x)
x = F.interpolate(x, scale_factor=4) # todo: check mode
feature_maps = x.permute([0,2,3,1])

N, H, W, C = feature_maps.shape
feature_maps = feature_maps.detach().cpu().numpy().reshape((-1, C))
feature_maps = StandardScaler().fit_transform(feature_maps)
feature_maps = feature_maps.reshape((N, -1, C))
# PCA torch
for i in range(feature_maps.shape[0]):
    feat = feature_maps[i]
    # feat = feat.reshape((-1, feat.shape[-1]))
    # mean = feat.mean(dim=0, keepdim=True)
    # std = feat.std(dim=0, keepdim=True)
    # feat = (feat - mean) / (std + 1e-6)
    # feat = StandardScaler().fit_transform(feat.detach().cpu().numpy())
    feat = torch.from_numpy(feat).to(device)
    U, S, V = torch.pca_lowrank(feat, center=False)
    low_dim_feat = feat @ V[:, :3]
    print(low_dim_feat.shape)
    low_dim_feat = low_dim_feat.detach().cpu().numpy()

    # plot

    low_dim_feat = (low_dim_feat - np.min(low_dim_feat))
    low_dim_feat /= np.max(low_dim_feat)
    feat_map = low_dim_feat.reshape((img_size, img_size, -1))

    plt.imsave(os.path.join('test_features', 'feat_{:03d}.jpg'.format(i)), feat_map)
    
    # plt.imshow(feat_map)
    # plt.show()