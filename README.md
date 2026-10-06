# jupyter-stata-colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/larsvilhuber/jupyter-stata-colab/blob/main/stata_colab_example.ipynb)

A minimal example of running Stata from a Jupyter notebook on [Google Colab](https://colab.research.google.com/).

- [`stata_colab_example.ipynb`](stata_colab_example.ipynb) – the example notebook.
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

The edition (`EDITION = "se"`) and Docker image (`IMAGE`) can be changed in the first code cell. An MP license can also run SE. To skip the prompt (e.g., in automated runs), set the environment variable `STATA_LIC_BASE64`.

## Outside of Colab

The helper also works on any x86-64 Linux machine:

```bash
sudo python3 setup_stata.py            # installs to /usr/local/stata, then prompts for the license
python3 setup_stata.py --help          # options: --image, --edition, --stata-dir, --root, --force, --skip-license
```

## License

You need your own valid Stata license. Stata is a product of StataCorp LLC; the Docker images are provided by the [AEA Data Editor](https://github.com/ssc-ng/docker-stata).
