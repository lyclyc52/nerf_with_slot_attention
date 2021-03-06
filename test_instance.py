import os
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ["CUDA_VISIBLE_DEVICES"]='5,6'
from model_instance import *
from load_blender import *
from run_nerf_helpers import *
from run_nerf import *
import torch



depth_file = 'data/nerf_synthetic/clevr_100_2objects/all_depths.npy'
depth_maps = np.load(depth_file)
depth_maps = depth_maps[..., None]
depth_maps = tf.compat.v1.image.resize_area(depth_maps, [256, 256]).numpy()
depth_maps = tf.squeeze(depth_maps, axis=-1).numpy()

weights_dir = './results/testing_1/weights'
img_dir = './results/testing_1/imgs'


os.makedirs(weights_dir, exist_ok=True)
os.makedirs(img_dir, exist_ok=True)


parser = config_parser()
args = parser.parse_args()

N_train = depth_maps.shape[0]

images, poses, render_poses, hwf, i_split = load_blender_data(
            args.datadir, args.half_res, args.testskip, size = 256)


# images, poses, render_poses, hwf = load_new_data(
#             args.datadir, args.half_res, args.testskip, size = 256)

model = Encoder_Decoder_nerf(hwf, vgg=True, separate_decoder=False, position_emb=False)


start_iter = 0
# model.load_weights(weights_dir,2000)


train_iters = 10000000

N_print=10
N_save = 500
N_imgs = 100
N_img = 500

images, depth_maps, poses = images[:N_imgs, :, :, :3], depth_maps[:N_imgs], poses[:N_imgs]
images, depth_maps, poses = torch.from_numpy(images), torch.from_numpy(depth_maps), torch.from_numpy(poses)

print('Start training')
for i in range(start_iter, train_iters):
    t = np.random.randint(0, 20, 4)
    # t = [0, 3, 25, 39]
    # t = [0, 1, 2, 3]

    input_images, input_depths, input_poses = images[t], depth_maps[t], poses[t]
    loss = model.update_grad(input_images, input_depths, input_poses, i)

    if i % N_print == 0:
        print('iter: {:06d},  loss: {:f}'.format(i, loss))


    if i % N_save == 0:
        model.save_weights(weights_dir, i)



    if i % N_img == 0: 
        val = np.random.randint(0, 20, 4)
        # val = [0, 3, 25, 39]
        # val = [0, 1, 2, 3]
        check = np.random.randint(0, 4)
        # check = 0
        val_images, val_depths, val_poses = images[val], depth_maps[val], poses[val]
        with torch.no_grad():
            rgb, masked_rgb_slots, unmasked_rgb_slots, attn = model.forward(val_images, val_depths, val_poses, isTrain=False)
            rgb = rgb.cpu().numpy()
            for s in range(len(masked_rgb_slots)):
                masked_rgb_slots[s] = masked_rgb_slots[s].cpu().numpy()
                unmasked_rgb_slots[s] = unmasked_rgb_slots[s].cpu().numpy()
            val_images = val_images.cpu().numpy()
            attn = attn.permute([3,0,1,2])
            attn = attn[..., None]
            attn = attn.expand([-1,-1,-1,-1, 3])
            attn = attn.cpu().numpy()
            # print(attn.shape)
            print('Saving images')
            imageio.imwrite(os.path.join(img_dir, 'val_{:06d}.jpg'.format(i)), to8b(rgb[check]))
            for j in range(len(masked_rgb_slots)):
                imageio.imwrite(os.path.join(img_dir, 'val_{:06d}_masked_slot{:01d}.jpg'.format(i,j)), to8b(masked_rgb_slots[j][check]))
                imageio.imwrite(os.path.join(img_dir, 'val_{:06d}_unmasked_slot{:01d}.jpg'.format(i,j)), to8b(unmasked_rgb_slots[j][check]))
                imageio.imwrite(os.path.join(img_dir, 'val_{:06d}_attn_map{:01d}.jpg'.format(i,j)), to8b(attn[j][check]))
            print('Done') 

        # imageio.imwrite(os.path.join('./imgs_1/gt_{:06d}.jpg'.format(i)), to8b(val_images[0]))
