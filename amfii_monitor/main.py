#insert mods here

#app imports
from app.logger import setup_logger, set_global_logger
from app.konstant import create_dir, load_paths

PROGRAM_NAME = "{{PROGRAM_NAME}}"


def main():
    config = load_paths()
    OUTPUT_DIR = config["output_path"]
    LOG_DIR = create_dir(OUTPUT_DIR, "log")

    logger = setup_logger(
        "watcher",
        base_dir=LOG_DIR,
        log_level=12,
        set_global=True
    )
    set_global_logger(logger)


if __name__ == "__main__":
    main()