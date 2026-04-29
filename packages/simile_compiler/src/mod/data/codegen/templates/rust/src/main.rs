use std::collections::HashMap;
use std::collections::HashSet;

use bidirectional_map::Bimap;

// Simile types
type Nat = u64;
type Int = i64;
type Float = f64;
type Pair<A, B> = (A, B);
type Relation<A, B> = Bimap<A, B>;

// TODO define custom relation (bidirectional map) type
// - make constructor take in list of pair type/tuple
// - add properties/traits to determine totality, surjectivity, injectivity, etc.
// - select implementations of methods that are most efficient for the relation type (with a fallback in case no type is specified)
