# ---
# args: ["--n-predict", "1024"]
# ---

# # Run large and small language models with llama.cpp (DeepSeek-R1, Phi-4)

# This example demonstrate how to run small (Phi-4) and large (DeepSeek-R1)
# language models on Modal with [`llama.cpp`](https://github.com/ggerganov/llama.cpp).

# By default, this example uses DeepSeek-R1 to produce a "Flappy Bird" game in Python --
# see the video below. The code used in the video is [here](https://gist.github.com/charlesfrye/a3788c61019c32cb7947f4f5b1c04818),
# along with the model's raw outputs.
# Note that getting the game to run required a small bugfix from a human --
# our jobs are still safe, for now.

# <center>
# <a href="https://gist.github.com/charlesfrye/a3788c61019c32cb7947f4f5b1c04818"> <video controls autoplay loop muted> <source src="https://modal-cdn.com/example-flap-py.mp4" type="video/mp4"> </video> </a>
# </center>

from pathlib import Path
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import date
from datetime import timedelta
import modal
import requests
import json


uri = "mongodb+srv://boilermaker2025:boilermaker2025@cluster0.uaozv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


client = MongoClient(uri, server_api=ServerApi('1'))

def fetch_from_mongo():
    local_prompt = '''Introduction
You are acting as a top-tier financial trader at a big firm. Your role is to analyse news data, legislation data, historical stock price data and analyse sentiments to determine which stocks should be bought or sold


# Output
Please provide output in the following format:
    <JSON_START>
    [{\"ticker\": \"STOCK1\", \"count\": 13 },
    { \"ticker\": \"STOCK2\", \"count\": 20 }]
    <JSON_END>
    <ADVICE_START>
	Insert here a properly formatted and concise explanation for why you should buy or sell a stock and the amount/ confidence level. Again, talk as if you are a quantitative trader at a top tier firm giving high value advice
    <ADVICE_END>
this is only an example for the format (json array with multiple json objects. I want to be able to parse this with json in python so make sure it is clean) you should include the stocks which you think are important
and include as many as possible.
here count is the amount left after buying/selling how much ever you recommend. that is, it is totalHoldings amount - yourrecommendSelling amount or + your RecommendedBuyingAmount
Try to think critically about the number to sell and to buy
Your advice within the advice tags should contain a <br> tag after each point/stock  and be foramtted in bullet points
You are  a professional stock broker so should maintian professionalism while reporting
# Provided information
You will receive the following information: recent news headlines, recently modified laws,
historical stock data from the previous day with tickers as well as
their open price, close price, highest price, lowest price, and number of transactions,
and currently held stock tickers with their quantities.

#Think quick and fast but be as accurate as possible
#All of my savings are dependent on your decisions
## Recent news headlines
'''
    db = client["News_And_Legislation_Info"]
    col = db["News"]
    x = col.find()
    news_string = " "
    for data in x:
        news_string += "-" + data["title"] + "-desc: " + data["description"] + "\n"
    col2 = db["Legislation"]
    y = col2.find()
    legislation_string = "These are the latest legislative laws passed: "
    for data in y:
        legislation_string += "-" + data["title"] + "-\n"
    local_prompt += news_string + "\n" + legislation_string
    current_holdings = "These are my current holdings :"
    col3 = db["Holdings"]
    z = col3.find()
    for data in z:
        current_holdings += "stock ticker: " + str(data["ticker"]) + " and stock amount: " + str(data["count"]) + " \n"
    print(current_holdings)
    local_prompt += current_holdings

    #getting todays date
    today = date.today()
    yesterday = str(today - timedelta(days = 3))
    myobj = { "from" : yesterday}
    
    
    stock_response = requests.post("https://jamestan-bmake2025-b-89.deno.dev/stocks", json = myobj)
    #print(stock_response)

    local_prompt += stock_response.text
    #stock_response = json.dumps(stock_response)
    #stock_response = stock_response.json()
    #col4 = db["Stock_Time_Series"]
    #a = col4.find()
    '''
    stock_data = "These are the historical prices for the stocks\n"
    for data in stock_response:
        stock_data += "Stock " + data["ticker"] + "had highest value: " + str(data["high"]) + " and lowest value: " + str(data["low"]) + " and open value of : " + str(data["open"]) + " and close value of: " + str(data["close"]) + " on the day of " +  str(data["date"]) + "\n"
    local_prompt += stock_data '''
    #local_prompt += current_holdings
    return local_prompt
#prompt = fetch_from_mongo()
# ## What GPU can run DeepSeek-R1? What GPU can run Phi-4?

# Our large model is a real whale:
# [DeepSeek-R1](https://api-docs.deepseek.com/news/news250120),
# which has 671B total parameters and so consumes over 100GB of storage,
# even when [quantized down to one ternary digit (1.58 bits)](https://unsloth.ai/blog/deepseekr1-dynamic)
# per parameter.

# To make sure we have enough room for it and its activations/KV cache,
# we select four L40S GPUs, which together have 192 GB of memory.

# [Phi-4](https://huggingface.co/microsoft/phi-4),
# on the other hand, is a svelte 14B total parameters,
# or roughly 5 GB when quantized down to
# [two bits per parameter](https://huggingface.co/unsloth/phi-4-GGUF).

# That's small enough that it can be comfortably run on a CPU,
# especially for a single-user setup like the one we'll build here.

GPU_CONFIG = "L40S:6"  # for DeepSeek-R1, literal `None` for phi-4

# ## Calling a Modal Function from the command line

# To start, we define our `main` function --
# the Python function that we'll run locally to
# trigger our inference to run on Modal's cloud infrastructure.

# This function, like the others that form our inference service
# running on Modal, is part of a Modal [App](https://modal.com/docs/guide/apps).
# Specifically, it is a `local_entrypoint`.
# Any Python code can call Modal Functions remotely,
# but local entrypoints get a command-line interface for free.

app = modal.App("example-llama-cpp")


@app.local_entrypoint()
def main(
    prompt: str = None,
    model: str = "DeepSeek-R1",  # or "phi-4"
    n_predict: int = -1,  # max number of tokens to predict, -1 is infinite
    args: str = None,  # string of arguments to pass to llama.cpp's cli
    fast_download: bool = None,  # download model before starting inference function
):
    """Run llama.cpp inference on Modal for phi-4 or deepseek r1."""
    import shlex
    import json
    org_name = "unsloth"

    # two sample models: the diminuitive phi-4 and the chonky deepseek r1
    if model.lower() == "phi-4":
        model_name = "phi-4-GGUF"
        quant = "Q2_K"
        model_entrypoint_file = f"phi-4-{quant}.gguf"
        model_pattern = f"*{quant}*"
        revision = None
        if args is not None:
            args = shlex.split(args)
    elif model.lower() == "deepseek-r1":
        model_name = "DeepSeek-R1-GGUF"
        quant = "UD-IQ1_S"
        model_entrypoint_file = (
            f"{model}-{quant}/DeepSeek-R1-{quant}-00001-of-00003.gguf"
        )
        model_pattern = f"*{quant}*"
        revision = "02656f62d2aa9da4d3f0cdb34c341d30dd87c3b6"
        if args is None:
            args = DEFAULT_DEEPSEEK_R1_ARGS
        else:
            args = shlex.split(args)
    else:
        raise ValueError(f"Unknown model {model}")

    repo_id = f"{org_name}/{model_name}"
    if fast_download or model.lower() == "deepseek-r1":
        download_model.remote(repo_id, [model_pattern], revision)

    # call out to a `.remote` Function on Modal for inference
    result = llama_cpp_inference.remote(
        model_entrypoint_file,
        prompt,
        n_predict,
        args,
        store_output=model.lower() == "deepseek-r1",
    )
    think_end = result.find("</think>")
    result = result[think_end: ]
    start_index = result.find("<JSON_START>") + 12
    end_index = result.find("<JSON_END>")
    json_string = result[start_index : end_index]
    cleaned_json_string = json_string.replace('`', '')
    json_data = json.loads(cleaned_json_string)

    db = client["News_And_Legislation_Info"]
    holdings = db["Holdings"]
    for stock in json_data:
        holdings.update_one({"ticker": stock["ticker"]},  # Match on the ticker field
        {"$set": {"count": stock["count"]}},  # Update the count field
        upsert=True
    )

    advice_start = result.find("<ADVICE_START>") + 14
    advice_end = result.find("</ADVICE_END>")
    advice_substring = result[advice_start : advice_end]
    advice_substring = advice_substring.replace('"', '')
    advice_substring = advice_substring.replace('\n', '')
    format_string = "{\"advice\": \"" + advice_substring + "\"}"

    big_string = cleaned_json_string + "\n" + format_string
    output_path = Path("./results") / f"llama-cpp-{model}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(big_string)

    advice_json = json.loads(format_string)
    advice_blob = db["Advice"]
    advice_blob.replace_one({}, advice_json, upsert=True)
    #output_path = Path("./results") / f"llama-cpp-{model}.txt"
    #output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"🦙 writing response to {output_path}")
    #big_string = cleaned_json_string + "\n" + format_string
    #output_path.write_text(big_string)


# You can trigger inference from the command line with

# ```bash
# modal run llama_cpp.py
# ```

# To try out Phi-4 instead, use the `--model` argument:

# ```bash
# modal run llama_cpp.py --model="phi-4"
# ```

# Note that this will run for up to 30 minutes, which costs ~$5.
# To allow it to proceed even if your local terminal fails,
# add the `--detach` flag after `modal run`.
# See below for details on getting the outputs.

# You can pass prompts with the `--prompt` argument and set the maximum number of tokens
# with the `--n-predict` argument.

# Additional arguments for `llama-cli` are passed as a string like `--args="--foo 1 --bar"`.

# For convenience, we set a number of sensible defaults for DeepSeek-R1,
# following the suggestions by the team at unsloth,
# who [quantized the model to 1.58 bit](https://unsloth.ai/blog/deepseekr1-dynamic).


DEFAULT_DEEPSEEK_R1_ARGS = [  # good default llama.cpp cli args for deepseek-r1
    "--cache-type-k",
    "q4_0",
    "--threads",
    "12",
    "-no-cnv",
    "--prio",
    "2",
    "--temp",
    "0.6",
    "--ctx-size",
    "20000",
]

# ## Compiling llama.cpp with CUDA support

# In order to run inference, we need the model's weights
# and we need code to run inference with those weights.

# [`llama.cpp`](https://github.com/ggerganov/llama.cpp)
# is a no-frills C++ library for running large language models.
# It supports highly-quantized versions of models ideal for running
# single-user language modeling services on CPU or GPU.

# We compile it, with CUDA support, and add it to a Modal
# [container image](https://modal.com/docs/guide/images)
# using the code below.

# For more details on using CUDA on Modal, including why
# we need to use the `nvidia/cuda` registry image in this case
# (hint: it's for the [`nvcc` compiler](https://modal.com/gpu-glossary/host-software/nvcc)),
# see the [Modal guide to using CUDA](https://modal.com/docs/guide/cuda).

LLAMA_CPP_RELEASE = "b4568"
MINUTES = 60

cuda_version = "12.4.0"  # should be no greater than host CUDA version
flavor = "devel"  #  includes full CUDA toolkit
operating_sys = "ubuntu22.04"
tag = f"{cuda_version}-{flavor}-{operating_sys}"


image = (
    modal.Image.from_registry(f"nvidia/cuda:{tag}", add_python="3.12")
    .apt_install(
        "git", "build-essential", "cmake", "curl", "libcurl4-openssl-dev"
    )
    .pip_install("pymongo")
    .pip_install("requests")
    .run_commands("git clone https://github.com/ggerganov/llama.cpp")
    .run_commands(
        "cmake llama.cpp -B llama.cpp/build "
        "-DBUILD_SHARED_LIBS=OFF -DGGML_CUDA=ON -DLLAMA_CURL=ON "
    )
    .run_commands(  # this one takes a few minutes!
        "cmake --build llama.cpp/build --config Release -j --clean-first --target llama-quantize llama-cli"
    )
    .run_commands("cp llama.cpp/build/bin/llama-* llama.cpp")
    .entrypoint([])  # remove NVIDIA base container entrypoint
)

# ## Storing models on Modal

# To make the model weights available on Modal,
# we download them from Hugging Face.

# Modal is serverless, so disks are by default ephemeral.
# To make sure our weights don't disappear between runs
# and require a long download step, we store them in a
# Modal [Volume](https://modal.com/docs/guide/volumes).

# For more on how to use Modal Volumes to store model weights,
# see [this guide](https://modal.com/docs/guide/model-weights).

model_cache = modal.Volume.from_name("llamacpp-cache", create_if_missing=True)
cache_dir = "/root/.cache/llama.cpp"

download_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("huggingface_hub[hf_transfer]==0.26.2")
    .pip_install("pymongo")
    .pip_install("requests")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)


@app.function(
    image=download_image, volumes={cache_dir: model_cache}, timeout=30 * MINUTES
)
def download_model(repo_id, allow_patterns, revision: str = None):
    from huggingface_hub import snapshot_download

    print(f"🦙 downloading model from {repo_id} if not present")

    snapshot_download(
        repo_id=repo_id,
        revision=revision,
        local_dir=cache_dir,
        allow_patterns=allow_patterns,
    )

    model_cache.commit()  # ensure other Modal Functions can see our writes before we quit

    print("🦙 model loaded")


# ## Storing model outputs on Modal

# Contemporary large reasoning models are slow --
# for the sample "flappy bird" prompt we provide,
# results are sometimes produced only after several (or even tens of) minutes.

# That makes their outputs worth storing.
# In addition to sending them back to clients,
# like our local command line,
# we'll store the results on a Modal Volume for safe-keeping.

results = modal.Volume.from_name("deepseek-strategy", create_if_missing=True)
results_dir = "/root/results"

# You can retrieve the results later in a number of ways.

# You can use the Volume CLI:

# ```bash
# modal volume ls llamacpp-results
# ```

# You can attach the Volume to a Modal `shell`
# to poke around in a familiar terminal environment:

# ```bash
# modal shell --volume llamacpp-results
# # then cd into /mnt
# ```

# Or you can access it from any other Python environment
# by using the same `modal.Volume` call as above to instantiate it:

# ```python
# results = modal.Volume.from_name("llamacpp-results")
# print(dir(results))  # show methods
# ```

# ## Running llama.cpp as a Modal Function

# Now, let's put it all together.

# At the top of our `llama_cpp_inference` function,
# we add an `app.function` decorator to attach all of our infrastructure:

# - the `image` with the dependencies
# - the `volumes` with the weights and where we can put outputs
# - the `gpu` we want, if any

# We also specify a `timeout` after which to cancel the run.

# Inside the function, we call the `llama.cpp` CLI
# with `subprocess.Popen`. This requires a bit of extra ceremony
# because we want to both show the output as we run
# and store the output to save and return to the local caller.
# For details, see the [Addenda section](#addenda) below.

# Alternatively, you might set up an OpenAI-compatible server
# using base `llama.cpp` or its [Python wrapper library](https://github.com/abetlen/llama-cpp-python)
# along with one of [Modal's decorators for web hosting](https://modal.com/docs/guide/webhooks).


@app.function(
    image=image,
    volumes={cache_dir: model_cache, results_dir: results},
    gpu=GPU_CONFIG,
    timeout=30 * MINUTES,
)
def llama_cpp_inference(
    model_entrypoint_file: str,
    prompt: str = None,
    n_predict: int = -1,
    args: list[str] = None,
    store_output: bool = True,
):
    import json
    import subprocess
    from uuid import uuid4


    prompt = fetch_from_mongo()

    if prompt is None:
        prompt = DEFAULT_PROMPT  # see end of file
    prompt = "<｜User｜>" + prompt + "<think>"
    if args is None:
        args = []

    # set layers to "off-load to", aka run on, GPU
    if GPU_CONFIG is not None:
        n_gpu_layers = 9999  # all
    else:
        n_gpu_layers = 0

    if store_output:
        result_id = str(uuid4())
        print(f"🦙 running inference with id:{result_id}")

    command = [
        "/llama.cpp/llama-cli",
        "--model",
        f"{cache_dir}/{model_entrypoint_file}",
        "--n-gpu-layers",
        str(n_gpu_layers),
        "--prompt",
        prompt,
        "--n-predict",
        str(n_predict),
    ] + args

    print("🦙 running commmand:", command, sep="\n\t")
    p = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False
    )

    stdout, stderr = collect_output(p)

    if p.returncode != 0:
        raise subprocess.CalledProcessError(
            p.returncode, command, stdout, stderr
        )

    if store_output:  # save results to a Modal Volume if requested
        print(f"🦙 saving results for {result_id}")
        result_dir = Path(results_dir) / result_id
        result_dir.mkdir(
            parents=True,
        )
        (result_dir / "out.txt").write_text(stdout)
        (result_dir / "err.txt").write_text(stderr)

    return stdout


# # Addenda

# The remainder of this code is less interesting from the perspective
# of running LLM inference on Modal but necessary for the code to run.

# For example, it includes the default "Flappy Bird in Python" prompt included in
# [unsloth's announcement](https://unsloth.ai/blog/deepseekr1-dynamic)
# of their 1.58 bit quantization of DeepSeek-R1.

DEFAULT_PROMPT = """ NA """

def stream_output(stream, queue, write_stream):
    """Reads lines from a stream and writes to a queue and a write stream."""
    for line in iter(stream.readline, b""):
        line = line.decode("utf-8", errors="replace")
        write_stream.write(line)
        write_stream.flush()
        queue.put(line)
    stream.close()


def collect_output(process):
    """Collect up the stdout and stderr of a process while still streaming it out."""
    import sys
    from queue import Queue
    from threading import Thread

    stdout_queue = Queue()
    stderr_queue = Queue()

    stdout_thread = Thread(
        target=stream_output, args=(process.stdout, stdout_queue, sys.stdout)
    )
    stderr_thread = Thread(
        target=stream_output, args=(process.stderr, stderr_queue, sys.stderr)
    )
    stdout_thread.start()
    stderr_thread.start()

    stdout_thread.join()
    stderr_thread.join()
    process.wait()

    stdout_collected = "".join(stdout_queue.queue)
    stderr_collected = "".join(stderr_queue.queue)

    return stdout_collected, stderr_collected
