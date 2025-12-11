"""View statistics and information about the vector database"""
import json
import faiss
import os
from datetime import datetime

INDEX_FILE = "ob3_index.faiss"
META_FILE = "ob3_metadata.json"


def show_db_stats():
    """Display comprehensive statistics about the vector database"""

    print("=" * 70)
    print("VECTOR DATABASE STATISTICS")
    print("=" * 70)

    # Check if files exist
    if not os.path.exists(INDEX_FILE):
        print(f"ERROR: {INDEX_FILE} not found")
        print(f"   Run build_vector_db.py to create the database first.")
        return

    if not os.path.exists(META_FILE):
        print(f"ERROR: {META_FILE} not found")
        return

    # Load index
    index = faiss.read_index(INDEX_FILE)

    # Load metadata
    with open(META_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # File information
    index_size = os.path.getsize(INDEX_FILE) / (1024 * 1024)  # MB
    meta_size = os.path.getsize(META_FILE) / (1024 * 1024)  # MB
    index_modified = datetime.fromtimestamp(os.path.getmtime(INDEX_FILE))
    meta_modified = datetime.fromtimestamp(os.path.getmtime(META_FILE))

    print("\nFILE INFORMATION:")
    print(f"   Index File:     {INDEX_FILE}")
    print(f"   Size:           {index_size:.2f} MB")
    print(f"   Last Modified:  {index_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n   Metadata File:  {META_FILE}")
    print(f"   Size:           {meta_size:.2f} MB")
    print(f"   Last Modified:  {meta_modified.strftime('%Y-%m-%d %H:%M:%S')}")

    # Index information
    print(f"\nINDEX STATISTICS:")
    print(f"   Total Badges:   {index.ntotal:,}")
    print(f"   Vector Dim:     {index.d}")
    print(f"   Index Type:     {type(index).__name__}")

    # Metadata information
    print(f"\nMETADATA STATISTICS:")
    print(f"   Total Entries:  {len(metadata):,}")

    # Verify synchronization
    if index.ntotal != len(metadata):
        print(f"\n   WARNING: Index and metadata are out of sync!")
        print(f"   Index: {index.ntotal} vectors")
        print(f"   Metadata: {len(metadata)} entries")
    else:
        print(f"\n   Index and metadata are synchronized")

    # Sample badge names
    if metadata:
        print(f"\nSAMPLE BADGES (first 5):")
        for i, entry in enumerate(metadata[:5], 1):
            badge_name = entry.get("name", "Unknown")
            print(f"   {i}. {badge_name}")

        if len(metadata) > 5:
            print(f"   ... and {len(metadata) - 5:,} more")

    # Latest badges (assume last added are at the end)
    if metadata:
        print(f"\nRECENTLY ADDED (last 5):")
        for i, entry in enumerate(metadata[-5:], 1):
            badge_name = entry.get("name", "Unknown")
            print(f"   {i}. {badge_name}")

    print("\n" + "=" * 70)


def search_badge_by_name(query: str):
    """Search for badges by name in metadata"""

    if not os.path.exists(META_FILE):
        print(f"ERROR: {META_FILE} not found")
        return

    with open(META_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    query_lower = query.lower()
    matches = []

    for idx, entry in enumerate(metadata):
        badge_name = entry.get("name", "")
        if query_lower in badge_name.lower():
            matches.append((idx, badge_name))

    if matches:
        print(f"\nFound {len(matches)} badge(s) matching '{query}':")
        for idx, name in matches:
            print(f"   [{idx}] {name}")
    else:
        print(f"\nNo badges found matching '{query}'")


def export_badge_names(output_file="badge_names.txt"):
    """Export all badge names to a text file"""

    if not os.path.exists(META_FILE):
        print(f"ERROR: {META_FILE} not found")
        return

    with open(META_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    with open(output_file, "w", encoding="utf-8") as f:
        for entry in metadata:
            badge_name = entry.get("name", "Unknown")
            f.write(f"{badge_name}\n")

    print(f"Exported {len(metadata)} badge names to {output_file}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "search" and len(sys.argv) > 2:
            search_query = " ".join(sys.argv[2:])
            search_badge_by_name(search_query)
        elif command == "export":
            output = sys.argv[2] if len(sys.argv) > 2 else "badge_names.txt"
            export_badge_names(output)
        else:
            print("Usage:")
            print("  python db_stats.py              # Show statistics")
            print("  python db_stats.py search QUERY # Search badges")
            print("  python db_stats.py export [FILE] # Export badge names")
    else:
        show_db_stats()
