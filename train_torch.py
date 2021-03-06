
import os
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ["CUDA_VISIBLE_DEVICES"]='1,2'
from model_torch import *
from load_blender import *
from run_nerf_helpers import *
from run_nerf import *




depth_file = 'data/nerf_synthetic/clevr_100_2objects/all_depths.npy'
depth_maps = np.load(depth_file)
depth_maps = depth_maps[..., None]
depth_maps = tf.compat.v1.image.resize_area(depth_maps, [128, 128]).numpy()
depth_maps = tf.squeeze(depth_maps, axis=-1).numpy()


parser = config_parser()
args = parser.parse_args()

N_train = depth_maps.shape[0]

images, poses, render_poses, hwf, i_split = load_blender_data(
            args.datadir, args.half_res, args.testskip)


model = Encoder_Decoder_nerf(hwf)


train_iters = 10000000

N_print=25

N_imgs = 100
N_img = 100

images, depth_maps, poses = images[:N_imgs, :, :, :3], depth_maps[:N_imgs], poses[:N_imgs]
images, depth_maps, poses = torch.from_numpy(images), torch.from_numpy(depth_maps), torch.from_numpy(poses)

print('Start training')
for i in range(0, train_iters):
    t = np.random.randint(0, N_imgs,4)
    input_images, input_depths, input_poses = images[t], depth_maps[t], poses[t]
    loss = model.update_grad(input_images, input_depths, input_poses, i)
    
    if i % N_print == 0:
        print('iter: {:06d},  loss: {:f}'.format(i, loss))


    # if i % N_print == 0:
    #     # save_weights_npy(model, i)
    #     ckpt_manager.save(i)
    

    if i % N_img == 0: 
        val = np.random.randint(0, N_imgs, 4)
        val_images, val_depths, val_poses = images[val], depth_maps[val], poses[val]
        with torch.no_grad():
            rgb,rgb_slots = model.forward(val_images, val_depths, val_poses, isTrain=False)
            rgb = rgb.numpy()
            rgb_slots = rgb_slots.numpy()

            val_images = val_images.numpy()
            imageio.imwrite(os.path.join('./imgs_1/val_{:06d}.jpg'.format(i)), to8b(rgb[0]))
            for j in range(3):
                imageio.imwrite(os.path.join('./imgs_1/val_slot{:01d}_{:06d}.jpg'.format(j,i)), to8b(rgb_slots[j][0]))

        # imageio.imwrite(os.path.join('./imgs_1/gt_{:06d}.jpg'.format(i)), to8b(val_images[0]))



