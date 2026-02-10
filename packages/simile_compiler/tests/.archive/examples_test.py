from src.mod.ast_ import *
from src.mod.parser import parse
from src.mod.analysis import semantic_analysis, populate_ast_environments, add_environments_to_ast
from src.mod.optimizer import (
    collection_optimizer,
    REWRITE_COLLECTION,
    SyntacticSugarForBags,
    BuiltinFunctions,
    ComprehensionConstructionCollection,
    DisjunctiveNormalFormCollection,
    OrWrappingCollection,
    GeneratorSelectionCollection,
    GSPToLoopsCollection,
    LoopsCodeGenerationCollection,
    ReplaceAndSimplifyCollection,
)

EXAMPLES = [
    (
        """
# Visitor Information System
Visitor := {Kevin, Michael, Charlie}
Room := {101, 102, 103}
Workshop := {SYNT, FM}

location: Workshop >-> Room := {
    SYNT |-> 101,
    FM |-> 102
}
attends: Visitor +-> Workshop := {
    Kevin |-> SYNT,
    Michael |-> FM
}

# Find all meals in room 101
meals_to_prep := card((location⁻¹ circ attends⁻¹)[{101}])
""",
    ),
    (
        """
# Warehouse Inventory System
Material := {TwoByFourPlank, HexBolt, Screw}
Price := {10,50,200}
Product := {Cabinet, Desk, Bookshelf}

catalogue: Material --> Price := {
    TwoByFourPlank |-> 200,
    HexBolt |-> 50,
    Screw |-> 10
}
inventory: bag(Material) := {|
    TwoByFourPlank |-> 100,
    HexBolt |-> 200,
    Screw |-> 300
|}
recipes: Product --> bag(Material) := {
    Cabinet |-> {
        TwoByFourPlank |-> 4,
        HexBolt |-> 8,
        Screw |-> 12
    },
    Desk |-> {
        TwoByFourPlank |-> 6,
        HexBolt |-> 10,
        Screw |-> 14
    },
    Bookshelf |-> {
        TwoByFourPlank |-> 8,
        HexBolt |-> 12,
        Screw |-> 16
    }
}

target_inventory: bag(Material) := {
    TwoByFourPlank |-> 1000,
    HexBolt |-> 2000,
    Screw |-> 3000
}
restocking_price := sum(catalogue[target_inventory \\ inventory])
""",
    ),
    (
        """
# Conway's Game of Life
Boundary: set(ℕ) := 0..10
Living: ℕ <-> ℕ := {
    1 |-> 1,
    4 |-> 2,
    9 |-> 5,
    1 |-> 7,
    8 |-> 3,
    4 |-> 7
}

neigh := {x |-> y, x_n |-> y_n · x in Boundary and y in Boundary and x in (x-1)..(x+1) and y in (y-1)..(y+1) and x != x_n and y != y_n | (x |-> y) |-> (x_n |-> y_n)}

next_step := {c · c in Living and card(neigh[{c}] /\\ Living) = 2 | c} \\/ {c · c in neigh[Living] and card(neigh[{c}] /\\ Living) = 3 | c}
""",
    ),
]

for (example,) in EXAMPLES[:1]:
    print("Running Example: ", example[1])
    ast = parse(example)
    # print("Parsed AST: ", ast.pretty_print())
    print("Parsed AST (algorithmic):")
    print(ast.pretty_print_algorithmic())
    ast = populate_ast_environments(ast)
    print("Analyzed AST: ", ast.pretty_print(print_env=True))
    ast = semantic_analysis(ast)
    print("Analyzed AST: ", ast.pretty_print(print_env=True))
    ast = collection_optimizer(ast, REWRITE_COLLECTION)
    # print("Post optimization AST: ", ast.pretty_print())
    print("Post optimization AST:\n\n", ast.pretty_print_algorithmic())
