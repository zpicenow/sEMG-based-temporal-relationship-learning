
# Code for thesis

This repo contains the code for the experiments in the papers: 
1. Yu Hu, Yongkang Wong, Wentao Wei, Yu Du, Mohan Kankanhalli, Weidong Geng. " [A novel attention-based hybrid CNN-RNN architecture for sEMG-based gesture recognition](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0206049)"
2. Yu Hu, Yongkang Wong, Qingfeng Dai, Mohan Kankanhalli, Weidong Geng. " [sEMG-based gesture recognition with embedded virtual hand poses and adversarial learning](https://ieeexplore.ieee.org/abstract/document/8766972/)"
## Requirements
- A CUDA compatible GPU
- Ubuntu >= 14.04 or any other Linux/Unix that can run Docker
- [Docker](http://docker.io/)
- [Nvidia Docker](https://github.com/NVIDIA/nvidia-docker)

## Usage
- **Pull docker image for the first paper**
    ``` 
    docker pull zjucapg/semg:latest
    ```
- **Pull docker image for the second paper**
    ```
    docker pull zjucapg/semgtf:latest  or  docker pull registry.cn-hangzhou.aliyuncs.com/semgtf/semgtf:latest
- **Dataset**
    
    Eleven databases including Ninapro DB1-DB7, CapgMyo DBa-DBc and CSL-HDEMG can be used for training and test.

    ```
    mkdir .cache
    # put NinaPro DB1 in .cache/ninapro-db1 or NinaPro DB7 in .cache/ninapro-db7
    # put CapgMyo DB-a in .cache/dba or DB-b in .cache/dbb or DB-c in .cache/dbc
    # put CSL-HDEMG in .cache/csl
    ```
    The NinaPro DB1 needs to be segmented by gesture labels and stored in Matlab format as follows.`.cache/ninapro-db1/data/sss/ggg/sss_ggg_ttt.mat` contains a field `data` reprensents the trial `ttt` of gesture `ggg` of subject `sss`. And numbers start from zero. Gesture 0 is the rest gesture.

    For instance, `.cache/ninapro-db1/data/000/001/000_001_000.mat` is the 0th trial of 1st gesture of the 0th subject. 
    
    You can download the original dataset from <https://www.idiap.ch/project/ninapro/database> or download the prepared dataset from our site <http://zju-capg.org/myo/data/ninapro-db1.zip>. CapgMyo and CSL-HDEMG datasets can be acquired on <http://zju-capg.org/myo/data> and <http://www.csl.uni-bremen.de/cms/forschung/bewegungserkennung>, respectively.

- **Quick Start**
    ```
    # Get into the capg/semg:mscnn container
    nvidia-docker run -ti -v your_projectdir:/code zjucapg/semg /bin/bash
    # first paper
    # Train
    sh scripts/exp.sh
    # Test
    python scripts/test.py
    
    # second paper
    # Train
    sh exp.sh
    # Test
    sh test.sh
    ```



## License
Licensed under an GPL v3.0 license.

## Bibtex
```
@article{hu2018novel,
  title={A novel attention-based hybrid CNN-RNN architecture for sEMG-based gesture recognition},
  author={Hu, Yu and Wong, Yongkang and Wei, Wentao and Du, Yu and Kankanhalli, Mohan and Geng, Weidong},
  journal={PloS one},
  volume={13},
  number={10},
  pages={e0206049},
  year={2018},
  publisher={Public Library of Science}
}
@article{hu2019semg,
  title={sEMG-Based Gesture Recognition With Embedded Virtual Hand Poses and Adversarial Learning},
  author={Hu, Yu and Wong, Yongkang and Dai, Qingfeng and Kankanhalli, Mohan and Geng, Weidong and Li, Xiangdong},
  journal={IEEE Access},
  volume={7},
  pages={104108--104120},
  year={2019},
  publisher={IEEE}
}
```