# src/utils/helpers.py
"""General utility functions, including logging setup."""
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(log_dir: Path, log_level: str = 'INFO'):
    """Configures logging to file and console manually without basicConfig."""
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"ERROR: Failed to create log directory {log_dir}: {e}", file=sys.stderr)
        return

    log_file = log_dir / f"processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    log_level_numeric = getattr(logging, log_level.upper(), None)
    if log_level_numeric is None:
         print(f"WARNING: Invalid log level '{log_level}'. Defaulting to INFO.", file=sys.stderr)
         log_level_numeric = logging.INFO

    root_logger = logging.getLogger()

    # --- MODIFICATION: REMOVE explicit handler removal loop ---
    # Let the test fixture handle cleanup between tests. This function will now ADD handlers.
    # If called multiple times without cleanup, it might add duplicates, but
    # for typical testing scenarios with fixtures, this should be okay.
    # for handler in root_logger.handlers[:]:
    #     try:
    #         handler.close()
    #     except Exception:
    #         pass
    #     root_logger.removeHandler(handler)
    # --- END MODIFICATION ---

    # Set the level on the root logger directly. This might affect pre-existing handlers.
    root_logger.setLevel(log_level_numeric)

    log_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(name)-15s - %(message)s',
        '%Y-%m-%d %H:%M:%S'
    )

    # Create and ADD File Handler
    file_handler = None
    # Prevent adding duplicate handlers of the same type/target if function runs repeatedly without cleanup
    if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == str(log_file) for h in root_logger.handlers):
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(log_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
             print(f"ERROR: Failed to create file handler for {log_file}: {e}", file=sys.stderr)

    # Create and ADD Stream Handler (to stdout)
    stream_handler = None
    # Prevent adding duplicate stdout stream handlers
    if not any(isinstance(h, logging.StreamHandler) and getattr(h, 'stream', None) == sys.stdout for h in root_logger.handlers):
        try:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(log_formatter)
            root_logger.addHandler(stream_handler)
        except Exception as e:
            print(f"ERROR: Failed to create stream handler: {e}", file=sys.stderr)


    # Check if handlers exist before logging confirmation
    if root_logger.hasHandlers(): # Check if *any* handler exists
        logging.info("Logging configured.")
        # Check specifically if OUR file handler was added before logging its path
        if any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == str(log_file) for h in root_logger.handlers):
            logging.info(f"Log file: {log_file}")
        logging.info(f"Log level: {logging.getLevelName(root_logger.getEffectiveLevel())}")
    else:
        # This case is less likely now unless both handler creations fail
        print(f"ERROR: No handlers configured for logging.", file=sys.stderr)


# --- Commented out simple log_message ---
# ... (rest of file) ...