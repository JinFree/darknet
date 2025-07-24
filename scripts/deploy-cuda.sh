#!/usr/bin/env bash

if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "Unable to deploy CUDA on macOS, please wait for a future script update"
  exit 1
elif [[ $(cut -f2 <<< $(lsb_release -i)) == "Ubuntu" ]]; then
  distr_name="$(cut -f2 <<< $(lsb_release -i) | tr '[:upper:]' '[:lower:]')$(cut -f2 <<< $(lsb_release -r) | tr -d '.')"
  arch_name="$(uname -m)"
  if [[ $arch_name == "x86_64" ]]; then
    arch_name="x86_64"
  elif [[ $arch_name == "aarch64" ]]; then
    arch_name="arm64"
  else
    echo "Unsupported architecture: $arch_name"
    exit 1
  fi
else
  echo "Unable to deploy CUDA on this OS, please wait for a future script update"
  exit 2
fi

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

if [ -f $script_dir/requested_cuda_version.sh ]; then
  source $script_dir/requested_cuda_version.sh
else
  echo "Unable to find requested_cuda_version.sh script"
  exit 3
fi

sudo apt-key del 7fa2af80
wget https://developer.download.nvidia.com/compute/cuda/repos/$distr_name/$arch_name/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y --no-install-recommends build-essential g++
sudo apt-get install -y --no-install-recommends apt-transport-https ca-certificates gnupg software-properties-common wget
sudo apt-get install -y --no-install-recommends zlib1g
sudo apt-get dist-upgrade -y
sudo apt-get install -y cuda-toolkit-${CUDA_VERSION_DASHED}
sudo apt-get install -y cudnn${CUDNN_MAJOR_VERSION}-cuda-${CUDA_MAJOR_VERSION}

sudo rm -rf /usr/local/cuda
sudo ln -s /usr/local/cuda-${CUDA_VERSION} /usr/local/cuda

sudo apt-get clean
