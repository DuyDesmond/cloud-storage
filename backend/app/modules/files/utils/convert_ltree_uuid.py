

# // Helper function to format UUID for PostgreSQL ltree
# export function uuidToLtree(uuid: string): string {
#   return uuid.replace(/-/g, '_');
# }

# export function ltreeToUuid(ltreeLabel: string): string {
#   return ltreeLabel.replace(/_/g, '-');
# }

# // Constructing a path: root_id.parent_id.child_id
# const path = [rootId, parentId, currentId].map(uuidToLtree).join('.');