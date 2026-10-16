inductive SimileType where
  | bool
  | int
  | set: SimileType -> SimileType
  | relation: SimileType -> SimileType -> SimileType
  | bag: SimileType -> SimileType
  | sequence: SimileType -> SimileType
  | tuple: List SimileType -> SimileType
  | procedure: List SimileType -> SimileType -> SimileType
  | type: SimileType -> SimileType
  -- | float
  -- | string
  -- | record
  -- | import
  deriving Repr
