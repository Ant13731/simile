import argparse
from loguru import logger

from src.mod.pipeline.scanner import scan
from src.mod.pipeline.parser import parse
from src.mod.pipeline.printer import ast_to_source
from src.mod.pipeline.analysis import SemanticAnalysis, semantic_analysis
from src.mod.pipeline.optimizer.v2 import lower_for_raw_python
from src.mod.pipeline.codegen import lower_to_raw_python


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simile Compiler")

    # DEBUG
    parser.add_argument("-t", "--tokenize", action="store_true", help="Print tokenized input")
    parser.add_argument("-p", "--parse", action="store_true", help="Part and print parsed code translated back to source")
    parser.add_argument("--parse_tree", action="store_true", help="Print parse tree")
    # parser.add_argument("-opt", "--optimize_ast", action="store_true", help="Print optimized AST")

    # Actual compilation options
    parser.add_argument("-c", "--cli", type=str, help="Parse the input string on the command line (overrides --input file)")
    parser.add_argument("-i", "--input", type=str, help="Input file name")
    parser.add_argument("-o", "--output", type=str, help="Output to a file with name")
    # TODO only raw_python intended to work now
    parser.add_argument("--output_as", type=str, help="Output simile code as: raw_python, python, rust")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    simile_input = None
    if args.cli:
        logger.info("Reading input from command line:", args.cli)
        simile_input = args.cli
    elif args.input:
        logger.info("Reading input from file:", args.input)
        with open(args.input, "r", encoding="utf-8") as file:
            simile_input = file.read()
    else:
        logger.info("No input provided. Please specify an input file or a command line string.")
        return

    if args.tokenize:
        logger.info("Tokenizing input:", simile_input)
        logger.info("Output:")
        logger.info(scan(simile_input))

    ast = parse(simile_input)
    if args.parse_tree:
        logger.info("Parsing input and pretty printing parse tree:")
        logger.info(ast)
    if args.parse:
        logger.info("Parsing input and pretty printing parse tree:")
        logger.info(ast_to_source(ast))

    sem_analysis = semantic_analysis(ast)
    if args.output_as == "raw_python":
        lowered_raw_semantic_analysis = lower_for_raw_python(sem_analysis)
        raw_python_output = lower_to_raw_python(lowered_raw_semantic_analysis)
        logger.info("Translated python output:")
        logger.info(raw_python_output)

        if args.output:
            logger.info(f"Writing raw python output to {args.output}")
            with open(args.output, "w") as fh:
                fh.write(raw_python_output)


if __name__ == "__main__":
    main()
