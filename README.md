# jupyter-stata-colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/larsvilhuber/jupyter-stata-colab/blob/main/stata_colab_example.ipynb) [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/larsvilhuber/jupyter-stata-colab/HEAD?urlpath=%2Fdoc%2Ftree%2Fstata_colab_example.ipynb)

A minimal example of running Stata from a Jupyter notebook on [Google Colab](https://colab.research.google.com/) or [repo2docker](https://repo2docker.readthedocs.io/).

- [`stata_colab_example.ipynb`](stata_colab_example.ipynb) – the example notebook.
- [`stata_colab_solutions.ipynb`](stata_colab_solutions.ipynb) – the same notebook, plus the cells from part 4 of the [Reproducible Documents tutorial](https://larsvilhuber.github.io/reproducible-documents/): a printable regression table and a figure, exported to Word and PDF. [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/larsvilhuber/jupyter-stata-colab/blob/main/stata_colab_solutions.ipynb) [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/larsvilhuber/jupyter-stata-colab/HEAD?urlpath=%2Fdoc%2Ftree%2Fstata_colab_solutions.ipynb). Generated from the tutorial's [cell files](https://github.com/larsvilhuber/reproducible-documents/tree/main/examples/04-jupyter-colab) by its `tests/build-notebook.py`.
- [`setup_stata.py`](setup_stata.py) – helper that installs Stata, writes your license, and starts [PyStata](https://www.stata.com/python/pystata19/).

## How it works

1. **Install Stata.** Colab cannot run Docker, so `setup_stata.py` downloads the layers of one of the [AEA Data Editor's Stata Docker images](https://hub.docker.com/u/dataeditors) (default: `dataeditors/stata19_5-se:2026-08-12`) straight from Docker Hub, using only the Python standard library, and extracts `/usr/local/stata`. These images do **not** contain a license.
2. **License.** The notebook prompts (hidden input) for your `stata.lic` **as a base64-encoded string**, decodes it, and writes it to `/usr/local/stata/stata.lic` on the temporary Colab machine. The license is never stored in the notebook.
3. **Run Stata.** Colab only offers Python (and R) kernels, so Stata is run through StataCorp's PyStata, which ships with Stata and provides the `%%stata` cell magic. Before PyStata is loaded, the license is checked in a separate process, because PyStata would otherwise crash the Colab session if the license is invalid.

## Usage

1. Base64-encode your license on your own computer and copy the resulting single line:

   ```bash
   base64 -w0 /usr/local/stata/stata.lic      # Linux
   base64 -i /Applications/Stata/stata.lic    # macOS
   ```

   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\Program Files\Stata19\stata.lic"))   # Windows
   ```

2. Click the **Open in Colab** badge above and run the cells in order (*Runtime → Run all*).
3. When prompted, paste the base64 string.
4. Write Stata code in cells that start with `%%stata`:

   ```stata
   %%stata
   sysuse auto, clear
   regress price mpg weight
   ```

The Stata version (`VERSION = "19_5"`), Docker tag (`TAG = "2026-08-12"`), and edition (`EDITION = "se"`) can be changed in the first code cell. Use the version spelling from the Docker image name (`19_5` means Stata 19.5). Set `TAG = "latest"` to query the Docker Hub API for the most recently updated non-`latest` tag: these images intentionally have no literal `latest` tag. You can also override the complete Docker image (`IMAGE`). An MP license can also run SE. To skip the prompt (e.g., in automated runs), set the environment variable `STATA_LIC_BASE64`.

The same settings are available through the Python helper:

```python
setup_stata.install_stata(version="19_5", tag="latest", edition="se")
```

An explicit `image=` overrides the version, tag, and edition used to select the image.

## repo2docker

On an x86-64 Linux machine with Docker and `jupyter-repo2docker` installed, run:

```bash
jupyter-repo2docker https://github.com/larsvilhuber/jupyter-stata-colab
```

To build a local checkout instead, run `jupyter-repo2docker .` from the repository directory. Open `stata_colab_example.ipynb` in the resulting Jupyter session and run its cells in order. Supply your own base64-encoded license at the hidden prompt, just as on Colab.

The `.binder/` configuration installs Stata's system libraries and fonts plus the Python packages used by the examples. Stata itself is downloaded when the notebook runs, into `~/usr/local/stata` for repo2docker's non-root user. No license is needed during the image build or baked into the image. Treat the running container as private: do not share it with your license installed, and remove it after use.

Both environments use the **same notebook and `setup_stata.py`**, including the version, tag, edition, installation, and license handling. There are no copied repo2docker Stata settings to synchronize, so changes to the Colab setup do not require a generated configuration or synchronization pull request.

## Other Linux machines

The helper also works on any x86-64 Linux machine:

```bash
sudo python3 setup_stata.py            # installs to /usr/local/stata, then prompts for the license
sudo python3 setup_stata.py --version 19_5 --tag latest --edition se
python3 setup_stata.py --help          # options: --version, --tag, --image, --edition, --stata-dir, --root, --force, --skip-license
```

## License

You need your own valid Stata license. Stata is a product of StataCorp LLC; the Docker images are provided by the [AEA Data Editor](https://github.com/ssc-ng/docker-stata).
