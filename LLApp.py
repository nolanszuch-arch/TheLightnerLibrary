import streamlit as st
import sqlite3


# ============================================================
# THE LIGHTNER LIBRARY
# ============================================================

st.set_page_config(
    page_title="The Lightner Library",
    page_icon="💿",
    layout="wide"
)


# -----------------------------
# DATABASE
# -----------------------------

connection = sqlite3.connect("lightner_library.db")
cursor = connection.cursor()


# -----------------------------
# TITLE
# -----------------------------

st.title("THE LIGHTNER LIBRARY")
st.divider()


# ============================================================
# SHELVING / FILING SYSTEM
#
# Change rules in THIS SECTION if the physical library
# organization changes in the future.
# ============================================================

import re


# Words ignored at the beginning of band names
IGNORED_BAND_WORDS = [
    "the "
]


def clean_artist_name(artist):
    """
    Removes Discogs numbering such as:
    'Artist Name (2)' -> 'Artist Name'
    """

    if not artist:
        return ""

    return re.sub(r"\s+\(\d+\)$", "", artist).strip()


def automatic_filing_name(artist, artist_type):
    """
    Determines how an album should be alphabetized.

    Person:
        David Bowie -> Bowie

    Band:
        The Doors -> Doors
        Pink Floyd -> Pink Floyd
    """

    artist = clean_artist_name(artist)

    if not artist:
        return ""

    # -----------------------------
    # BAND / GROUP
    # -----------------------------

    if artist_type == "group":

        lower_artist = artist.lower()

        for word in IGNORED_BAND_WORDS:

            if lower_artist.startswith(word):
                return artist[len(word):]

        return artist


    # -----------------------------
    # SOLO ARTIST
    # -----------------------------

    words = artist.split()

    if len(words) > 1:
        return words[-1]

    return artist


def get_filing_name(
        artist,
        artist_type,
        manual_override=None
):

    """
    Manual overrides ALWAYS win.
    """

    if manual_override:

        manual_override = manual_override.strip()

        if manual_override:
            return manual_override

    return automatic_filing_name(
        artist,
        artist_type
    )


def get_filing_letter(filing_name):
    """
    Bowie -> B
    Doors -> D
    Star Wars -> S
    """

    if not filing_name:
        return "#"

    for character in filing_name.upper():

        if character.isalnum():
            return character

    return "#"

# ============================================================
# FIND ALBUMS NEXT TO EACH OTHER ON THE SHELF
# ============================================================

def get_neighbor_albums(album_id):

    cursor.execute("""
        SELECT
            id,
            artist,
            album,
            filing_name,
            filing_letter

        FROM albums

        ORDER BY
            filing_name COLLATE NOCASE,
            artist COLLATE NOCASE,
            year,
            album COLLATE NOCASE,
            id
    """)

    sorted_albums = cursor.fetchall()

    for index, record in enumerate(sorted_albums):

        current_id = record[0]

        if current_id == album_id:

            previous_album = None
            next_album = None

            if index > 0:
                previous_album = sorted_albums[index - 1]

            if index < len(sorted_albums) - 1:
                next_album = sorted_albums[index + 1]

            return previous_album, next_album

    return None, None

# ============================================================
# ALBUM DETAIL FUNCTION
# ============================================================

def show_album(album_id):
    cursor.execute("""
        SELECT
            id,
            discogs_id,
            artist,
            album,
            year,
            genre,
            style,
            format,
            image_url,
            low_price,
            median_price,
            high_price,
            shelf,
            position,
            notes,
            artist_type,
            filing_override,
            filing_name,
            filing_letter
        FROM albums
        WHERE id = ?
    """, (album_id,))

    album_data = cursor.fetchone()

    if album_data is None:
        st.error("Album could not be found.")
        return

    (
        database_id,
        discogs_id,
        artist,
        album,
        year,
        genre,
        style,
        album_format,
        image_url,
        low_price,
        median_price,
        high_price,
        shelf,
        position,
        notes,
        artist_type,
        filing_override,
        filing_name,
        filing_letter
    ) = album_data

    # -----------------------------
    # BACK BUTTON
    # -----------------------------

    if st.button("← Back to Library"):
        st.session_state.selected_album = None
        st.rerun()

    st.divider()

    # -----------------------------
    # ALBUM INFORMATION
    # -----------------------------

    cover_column, info_column = st.columns([1, 2])

    with cover_column:

        if image_url:
            st.image(image_url, width=300)

    with info_column:

        st.header(album)
        st.subheader(artist)

        if year:
            st.write(f"**Year:** {year}")

        if genre:
            st.write(f"**Genre:** {genre}")

        if style:
            st.write(f"**Style:** {style}")

        if album_format:
            st.write(f"**Format:** {album_format}")

        st.caption(f"Discogs Release ID: {discogs_id}")

    st.divider()

    # ============================================================
    # SHELVING / FILING INFORMATION
    # ============================================================

    st.subheader("📚 Filing Location")

    st.write(
        f"### File Under: {filing_letter if filing_letter else '#'}"
    )

    if filing_name:
        st.write(
            f"Alphabetized as: **{filing_name}**"
        )

    if artist_type:
        st.caption(
            f"Automatic artist type: {artist_type}"
        )

    # -----------------------------
    # RECORDS NEXT TO THIS ONE
    # -----------------------------

    previous_album, next_album = get_neighbor_albums(
        database_id
    )

    st.markdown("#### Find it between:")

    # Previous record
    if previous_album:

        previous_artist = previous_album[1]
        previous_title = previous_album[2]

        st.write(
            f"⬅️ **{previous_artist} — {previous_title}**"
        )

    else:

        st.write("⬅️ Beginning of collection")

    # Current record
    st.write(
        f"🎵 **{artist} — {album}**"
    )

    # Next record
    if next_album:

        next_artist = next_album[1]
        next_title = next_album[2]

        st.write(
            f"➡️ **{next_artist} — {next_title}**"
        )

    else:

        st.write("➡️ End of collection")

    st.divider()

    # -----------------------------
    # MANUAL FILING OVERRIDE
    # -----------------------------

    new_filing_override = st.text_input(
        "Manual Filing Name",
        value=filing_override if filing_override else "",
        help=(
            "Leave blank to use automatic filing. "
            "For example, enter 'Star Wars' for a soundtrack "
            "you want filed under S."
        ),
        key=f"filing_override_{database_id}"
    )

    if new_filing_override:

        preview_name = new_filing_override.strip()

    else:

        preview_name = filing_name

    if preview_name:

        preview_letter = preview_name[0].upper()

    else:

        preview_letter = "#"

    st.info(
        f"This record will be filed under **{preview_letter}** "
        f"as **{preview_name}**."
    )

    st.divider()


    # -----------------------------
    # LOCATION
    # -----------------------------

    st.subheader("📍 Location")

    location1, location2 = st.columns(2)

    with location1:

        new_shelf = st.text_input(
            "Shelf",
            value=shelf if shelf else "",
            key=f"shelf_{database_id}"
        )

    with location2:

        new_position = st.number_input(
            "Position",
            min_value=0,
            value=position if position is not None else 0,
            step=1,
            key=f"position_{database_id}"
        )

    # -----------------------------
    # NOTES
    # -----------------------------

    st.subheader("📝 Notes")

    new_notes = st.text_area(
        "Album Notes",
        value=notes if notes else "",
        height=150,
        key=f"notes_{database_id}"
    )

    # -----------------------------
    # SAVE
    # -----------------------------

    if st.button(
            "Save Changes",
            type="primary",
            key=f"save_{database_id}"
    ):
        # ========================================================
        # CALCULATE FINAL FILING LOCATION
        # ========================================================

        final_filing_name = get_filing_name(
            artist,
            artist_type,
            new_filing_override
        )

        final_filing_letter = get_filing_letter(
            final_filing_name
        )

        # ========================================================
        # SAVE CHANGES TO DATABASE
        # ========================================================

        cursor.execute("""
            UPDATE albums

            SET
                shelf = ?,
                position = ?,
                notes = ?,
                filing_override = ?,
                filing_name = ?,
                filing_letter = ?

            WHERE id = ?
        """, (
            new_shelf,
            new_position,
            new_notes,
            new_filing_override.strip(),
            final_filing_name,
            final_filing_letter,
            database_id
        ))

        connection.commit()

        st.success(
            f"Saved! This record is filed under "
            f"{final_filing_letter} as {final_filing_name}."
        )

        st.rerun()

# ============================================================
# SESSION STATE
# ============================================================

if "selected_album" not in st.session_state:
    st.session_state.selected_album = None


# ============================================================
# SELECTED ALBUM
# ============================================================

if st.session_state.selected_album is not None:

    show_album(st.session_state.selected_album)


# ============================================================
# MAIN APP
# ============================================================

else:

    # -----------------------------
    # COLLECTION COUNT
    # -----------------------------

    cursor.execute("SELECT COUNT(*) FROM albums")
    album_count = cursor.fetchone()[0]

    # -----------------------------
    # NAVIGATION
    # -----------------------------

    library_tab, search_tab = st.tabs([
        "📚 Library",
        "🔎 Search"
    ])


    # ========================================================
    # LIBRARY
    # ========================================================

    with library_tab:

        st.header("Your Collection")

        st.metric(
            "Albums",
            album_count
        )

        st.divider()

        cursor.execute("""
            SELECT
                id,
                artist,
                album,
                year,
                genre,
                image_url,
                shelf,
                position,
                filing_name,
                filing_letter

            FROM albums

            ORDER BY
                filing_name COLLATE NOCASE,
                artist COLLATE NOCASE,
                year,
                album COLLATE NOCASE
        """)

        albums = cursor.fetchall()

        for album_data in albums:

            (
                database_id,
                artist,
                album,
                year,
                genre,
                image_url,
                shelf,
                position,
                filing_name,
                filing_letter
            ) = album_data

            cover_column, info_column = st.columns([1, 4])

            with cover_column:

                if image_url:
                    st.image(
                        image_url,
                        width=150
                    )

            with info_column:

                st.subheader(album)

                st.write(f"**Artist:** {artist}")
                if filing_name:
                    st.write(
                        f"📚 **File Under: {filing_letter} — {filing_name}**"
                    )

                if year:
                    st.write(f"**Year:** {year}")

                if genre:
                    st.write(f"**Genre:** {genre}")

                if shelf:

                    st.write(
                        f"📍 **Shelf {shelf} — Position {position}**"
                    )

                else:

                    st.write(
                        "📍 **Location not assigned**"
                    )

                if st.button(
                    "View Album",
                    key=f"library_{database_id}"
                ):

                    st.session_state.selected_album = database_id
                    st.rerun()

            st.divider()


    # ========================================================
    # SEARCH
    # ========================================================

    with search_tab:

        st.header("Search The Lightner Library")

        search = st.text_input(
            "Search by artist, album, or genre"
        )

        if search:

            search_words = search.lower().split()

            cursor.execute("""
                SELECT
                    id,
                    artist,
                    album,
                    year,
                    genre,
                    image_url,
                    shelf,
                    position,
                    filing_name,
                    filing_letter

                FROM albums
            """)

            all_albums = cursor.fetchall()

            results = []

            for album_data in all_albums:

                (
                    database_id,
                    artist,
                    album,
                    year,
                    genre,
                    image_url,
                    shelf,
                    position,
                    filing_name,
                    filing_letter
                ) = album_data

                artist = artist or ""
                album = album or ""
                genre = genre or ""

                searchable_text = (
                    artist + " " +
                    album + " " +
                    genre
                ).lower()

                if all(
                    word in searchable_text
                    for word in search_words
                ):
                    results.append(album_data)

            st.write(
                f"**{len(results)} result(s) found**"
            )

            st.divider()

            for album_data in results:

                (
                    database_id,
                    artist,
                    album,
                    year,
                    genre,
                    image_url,
                    shelf,
                    position,
                    filing_name,
                    filing_letter
                ) = album_data

                cover_column, info_column = st.columns([1, 4])

                with cover_column:

                    if image_url:
                        st.image(
                            image_url,
                            width=150
                        )

                with info_column:

                    st.subheader(album)

                    st.write(
                        f"**Artist:** {artist}"
                    )

                    # --------------------------------
                    # FILING LOCATION
                    # --------------------------------

                    if filing_name:
                        st.write(
                            f"📚 **File Under: {filing_letter} — {filing_name}**"
                        )

                    # --------------------------------
                    # FIND RECORDS NEXT TO THIS ONE
                    # --------------------------------

                    previous_album, next_album = get_neighbor_albums(
                        database_id
                    )

                    st.markdown("#### Find it between:")

                    # PREVIOUS RECORD

                    if previous_album:

                        previous_artist = previous_album[1]
                        previous_title = previous_album[2]

                        st.write(
                            f"⬅️ **{previous_artist} — {previous_title}**"
                        )

                    else:

                        st.write(
                            "⬅️ Beginning of collection"
                        )

                    # CURRENT RECORD

                    st.write(
                        f"🎵 **{artist} — {album}**"
                    )

                    # NEXT RECORD

                    if next_album:

                        next_artist = next_album[1]
                        next_title = next_album[2]

                        st.write(
                            f"➡️ **{next_artist} — {next_title}**"
                        )

                    else:

                        st.write(
                            "➡️ End of collection"
                        )

                    # --------------------------------
                    # OTHER INFORMATION
                    # --------------------------------

                    if year:
                        st.write(
                            f"**Year:** {year}"
                        )

                    if genre:
                        st.write(
                            f"**Genre:** {genre}"
                        )

                    # --------------------------------
                    # VIEW ALBUM
                    # --------------------------------

                    if st.button(
                            "View Album",
                            key=f"search_{database_id}"
                    ):
                        st.session_state.selected_album = database_id
                        st.rerun()

                st.divider()


connection.close()