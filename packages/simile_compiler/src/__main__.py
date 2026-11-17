import argparse
from loguru import logger

from src.mod import scan, parse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simile Compiler")

    # DEBUG
    parser.add_argument("-t", "--tokenize", action="store_true", help="Print tokenized input")
    parser.add_argument("-pp", "--pretty_print_parse", action="store_true", help="Print parse tree")
    parser.add_argument("-opt", "--optimize_ast", action="store_true", help="Print optimized AST")

    # Actual compilation options
    parser.add_argument("-c", "--cli", type=str, help="Parse the input string on the command line (overrides --input file)")
    parser.add_argument("-i", "--input", type=str, help="Input file name")
    parser.add_argument("-o", "--output", type=str, help="Output file name")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    simile_input = None
    if args.cli:
        logger.info("Parsing input from command line:", args.cli)
        simile_input = args.cli
    elif args.input:
        logger.info("Parsing input from file:", args.input)
        with open(args.input, "r", encoding="utf-8") as file:
            simile_input = file.read()
    else:
        logger.info("No input provided. Please specify an input file or a command line string.")
        return

    if args.tokenize:
        logger.info("Tokenizing input:", simile_input)
        logger.info("Output:")
        logger.info(scan(simile_input))

    if args.pretty_print_parse:
        logger.info("Parsing input and pretty printing parse tree:", simile_input)


if __name__ == "__main__":
    main()
