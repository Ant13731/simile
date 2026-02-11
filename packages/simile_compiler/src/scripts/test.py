from src.mod import parse
from src.mod import ast_
from src.mod import analysis
from src.mod import collection_optimizer, REWRITE_COLLECTION
from src.mod import RustCodeGenerator, CPPCodeGenerator
from src.mod import scan


scan("")


# TEST = ast_.Start(
#     ast_.Statements(
#         [
#             ast_.Sum(
#                 ast_.And(
#                     [
#                         ast_.In(
#                             ast_.Identifier("s"),
#                             ast_.SetEnumeration(
#                                 [ast_.Int("1"), ast_.Int("2")],
#                             ),
#                         ),
#                     ]
#                 ),
#                 ast_.Int("1"),
#             ),
#         ]
#     )
# )
# TEST_STR = "card({s · s in {1, 2} | s})"

# print("TEST_STR:", TEST_STR)
# # print("TEST:", TEST.pretty_print())
# parsed_test_str = parse(TEST_STR)
# print(parsed_test_str.body.items[0]._bound_identifiers)
# # print("PARSED TEST_STR:", parsed_test_str.pretty_print())
# analyzed_test = analysis.populate_ast_environments(TEST)
# analyzed_test_str = analysis.populate_ast_environments(parsed_test_str)
# # print("ANALYZED TEST:", analyzed_test.pretty_print())
# # print("ANALYZED PARSED TEST_STR:", analyzed_test_str.pretty_print())
# # comp_constr_test = SetComprehensionConstructionCollection().normalize(analyzed_test)
# comp_constr_test_str1 = SetComprehensionConstructionCollection().normalize(analyzed_test_str)
# comp_constr_test_str2 = DisjunctiveNormalFormQuantifierPredicateCollection().normalize(comp_constr_test_str1)
# comp_constr_test_str3 = SetCodeGenerationCollection().normalize(comp_constr_test_str2)
# # print("COMP CONSTR TEST:", comp_constr_test.pretty_print())
# print(parsed_test_str.body.items[0]._bound_identifiers)
# print(analyzed_test_str.body.items[0]._bound_identifiers)
# print(comp_constr_test_str1.body.items[0]._bound_identifiers)
# print(comp_constr_test_str2.body.items[0]._bound_identifiers)
# # print(comp_constr_test_str3.body.items[0]._bound_identifiers)
# print("COMP CONSTR TEST STR:", comp_constr_test_str1.pretty_print())
# print("COMP CONSTR TEST STR:", comp_constr_test_str2.pretty_print())
# print("COMP CONSTR TEST STR:", comp_constr_test_str3.pretty_print())

# TEST_STR = "card({s · s in {1, 2} or s in {2, 3} | s})"
# TEST_STR = "card({1, 2} \\/ {2, 3})"
# TEST_STR = "card({s · s in {1, 2} | s})"
# TEST_STR = "{s,e · s in {1, 2} and e in {2, 3} | s |-> e}"
# TEST_STR = "{s · s in { x + 1 | x in {1, 2} or x in {4}} or s in { x + 2 | x in {2, 3}} | s}"
# TEST_STR = "{1, 2} \\/ {2, 3}"
# len({1, 2} - {2, 3})

# print("TEST_STR 2:", TEST_STR)

# ast: ast_.ASTNode | list = parse(TEST_STR)
# if isinstance(ast, list):
#     raise ValueError(f"Expected a single AST, got a list (parsing failed): {ast}")

# ast = analysis.populate_ast_environments(ast)
# print("PARSED TEST_STR:", ast.pretty_print())
# print("PARSED TEST_STR:", ast.pretty_print_algorithmic())

# ast = collection_optimizer(ast, SET_REWRITE_COLLECTION[:-2])
# print("OPTIMIZED TEST_STR:", ast.pretty_print())
# # print("OPTIMIZED TEST_STR:", ast.pretty_print(print_env=True))
# print("OPTIMIZED TEST_STR:", ast.pretty_print_algorithmic())

# ast = analysis.populate_ast_environments(ast)
# print("OPTIMIZED TEST_STR:", ast.pretty_print())
# print("OPTIMIZED TEST_STR:", ast.pretty_print(print_env=True))
# print("OPTIMIZED TEST_STR:", ast.pretty_print_algorithmic())

# RustCodeGenerator(ast).build()


# TEST_STR_TO_GET_AST = f"""
# counter := 0
# for s in {{1,2}}:
#     expr_var := s
#     counter := counter + 1
# for q in {{2,3}}:
#     expr_var := q
#     if ¬(q ∈ {{1, 2}} ∧ expr_var = q):
#         counter := counter + 1
# """
# ast_to_get = parse(TEST_STR_TO_GET_AST)
# print("TEST_STR_TO_GET_AST:", TEST_STR_TO_GET_AST)
# print("AST TO GET:", ast_to_get.pretty_print())


# print(
#     ast_.structurally_equal(
#         ast,
#         ast_to_get,
#     )
# )


# comp_constr_test_str = SetComprehensionConstructionCollection().normalize(analyzed_test_str)
# print("COMP CONSTR TEST STR 2 1:", comp_constr_test_str.pretty_print())
# comp_constr_test_str = DisjunctiveNormalFormQuantifierPredicateCollection().normalize(comp_constr_test_str)
# print("COMP CONSTR TEST STR 2 2:", comp_constr_test_str.pretty_print())
# comp_constr_test_str = PredicateSimplificationCollection().normalize(comp_constr_test_str)
# print("COMP CONSTR TEST STR 2 3:", comp_constr_test_str.pretty_print())
# comp_constr_test_str = GeneratorSelectionCollection().normalize(comp_constr_test_str)
# print("COMP CONSTR TEST STR 2 4:", comp_constr_test_str.pretty_print())
# # print("COMP CONSTR TEST STR 2:", comp_constr_test_str3.body.items[0]._selected_generators)
# comp_constr_test_str = SetCodeGenerationCollection().normalize(comp_constr_test_str)
# print("COMP CONSTR TEST STR 2 5:", comp_constr_test_str.pretty_print())
# print(parsed_test_str.pretty_print_algorithmic())
# print(comp_constr_test_str.pretty_print_algorithmic())

# R := {x |-> y | x |-> y in {1 |-> 2}}
# TEST_STR = """
# {s · s in ({ t · t in {1, 2} | t } \\/ {3}) | s}
# """
# ast: ast_.ASTNode = parse(TEST_STR)
# ast = analysis.semantic_analysis(ast)

# ast = collection_optimizer(ast, SET_REWRITE_COLLECTION)
# from src.mod.optimizer.rewrite_collections import SetComprehensionConstructionCollection as S1
# from src.mod.optimizer.rewrite_collections import (
#     SyntacticSugarForBags,
#     SyntacticSugarForSequences,
#     BuiltinFunctions,
#     ComprehensionConstructionCollection,
#     DisjunctiveNormalFormCollection,
#     OrWrappingCollection,
#     GeneratorSelectionCollection,
#     GSPToLoopsCollection,
#     RelationalSubtypingLoopSimplification,
#     LoopsCodeGenerationCollection,
#     ReplaceAndSimplifyCollection,
# )

# # ast = S1().normalize(ast)
# # print("PARSED TEST_STR:", ast.pretty_print(print_env=True))
# # print("PARSED TEST_STR:", ast.pretty_print_algorithmic())
# # print("PARSED TEST_STR:", ast.body.items[0])
# # print("PARSED TEST_STR:", ast.body.items[0].predicate.items[1].items[0].right._bound_identifiers)

# TEST_STR = """
# location: str >-> int := {"SYNT" |-> 100, "ABC" |-> 200, "CDP" |-> 300}
# attends: str +-> str := {"Alice" |-> "SYNT", "Bob" |-> "ABC", "Charlie" |-> "SYNT"}

# room := 100

# num_meals := card((location~ circ attends~)[{room}])
# print(num_meals)
# """

# # Optimizer doesnt work - type system not strong enough for generics...
# # TEST_STR = """
# # catalogue: str --> float := {"2by4Plank" |-> 3.50, "HexBolt" |-> 0.25, "Nails" |-> 0.10}
# # inventory: bag[str] := {"2by4Plank" |-> 50, "HexBolt" |-> 200, "Nails" |-> 1000}
# # recipes: str --> bag[str] := {
# #     "Cabinet" |-> {"2by4Plank" |-> 7, "HexBolt" |-> 10, "Nails" |-> 10},
# #     "Bookshelf" |-> {"2by4Plank" |-> 1, "HexBolt" |-> 0, "Nails" |-> 4},
# #     "Desk" |-> {"2by4Plank" |-> 10, "HexBolt" |-> 40, "Nails" |-> 100}
# # }

# # target_inventory: bag[str] := {"2by4Plank" |-> 100, "HexBolt" |-> 500, "Nails" |-> 5000}

# # restocking_price := sum({p |-> n · p |-> n in catalogue~ circ (inventory \\ target_inventory) | p * n})
# # """

# ast: ast_.ASTNode = parse(TEST_STR)
# ast = analysis.semantic_analysis(ast)

# print("PARSED TEST_STR:", ast.pretty_print(print_env=True))
# print("PARSED TEST_STR:", ast.pretty_print_algorithmic())

# ast = SyntacticSugarForBags().normalize(ast)
# ast = SyntacticSugarForSequences().normalize(ast)
# ast = ComprehensionConstructionCollection().normalize(ast)
# ast = BuiltinFunctions().normalize(ast)
# ast = ComprehensionConstructionCollection().normalize(ast)
# ast = DisjunctiveNormalFormCollection().normalize(ast)
# ast = OrWrappingCollection().normalize(ast)
# ast = GeneratorSelectionCollection().normalize(ast)
# ast = GSPToLoopsCollection().normalize(ast)
# ast = RelationalSubtypingLoopSimplification().normalize(ast)
# ast = LoopsCodeGenerationCollection().normalize(ast)
# ast = ReplaceAndSimplifyCollection().normalize(ast)
# print("OPTIMIZED TEST_STR:", ast.pretty_print(print_env=False))
# print("OPTIMIZED TEST_STR:", ast.pretty_print_algorithmic())

# RustCodeGenerator(ast).build()
