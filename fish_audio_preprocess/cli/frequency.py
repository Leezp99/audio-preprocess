import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Union

import click
import librosa
import numpy as np
from loguru import logger
from matplotlib import pyplot as plt
from tqdm import tqdm

from fish_audio_preprocess.utils.file import list_files


def count_notes_from_file(file: Union[Path, str]) -> Counter:
    """Count the notes from a file

    Args:
        file (Union[Path, str]): The file to count the notes from

    Returns:
        Counter: A counter of the notes
    """

    import parselmouth as pm

    pitch_ac = pm.Sound(str(file)).to_pitch_ac()
    f0 = pitch_ac.selected_array["frequency"]

    counter = Counter()
    for i in f0:
        if np.isinf(i) or np.isnan(i) or i == 0:
            continue

        counter[librosa.hz_to_note(i)] += 1

    return counter


@click.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--recursive/--no-recursive", default=True, help="Search recursively")
@click.option(
    "--visualize/--no-visualize", default=True, help="Visualize the distribution"
)
@click.option(
    "--num-workers",
    default=os.cpu_count(),
    help="Number of workers for parallel processing",
)
def frequency(
    input_dir: str,
    recursive: bool,
    visualize: bool,
    num_workers: int,
):
    """
    Get the frequency of all audio files in a directory
    """

    input_dir = Path(input_dir)
    files = list_files(input_dir, {".wav"}, recursive=recursive)
    logger.info(f"Found {len(files)} files, calculating frequency")

    counter = Counter()

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        tasks = []

        for file in tqdm(files, desc="Preparing"):
            tasks.append(executor.submit(count_notes_from_file, file))

        for task in tqdm(
            as_completed(tasks), desc="Collecting infos", total=len(tasks)
        ):
            assert task.exception() is None
            counter += task.result()

    data = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)

    for note, count in data:
        logger.info(f"{note}: {count}")

    if visualize is False:
        return

    x_axis_order = librosa.midi_to_note(list(range(0, 300)))
    data = sorted(counter.items(), key=lambda kv: x_axis_order.index(kv[0]))

    plt.rcParams["figure.figsize"] = [10, 4]
    plt.rcParams["figure.autolayout"] = True
    plt.bar([x[0] for x in data], [x[1] for x in data])
    plt.xticks(rotation=90)
    plt.title("Notes distribution")
    plt.xlabel("Notes")
    plt.ylabel("Count")
    plt.show()


if __name__ == "__main__":
    frequency()