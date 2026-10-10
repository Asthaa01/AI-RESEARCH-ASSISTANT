import re
from collections import Counter
from pathlib import Path
import streamlit as st
import pandas as pd
import sqlite3
from ai_comparison import compare_papers
from similarity import (
    find_similar_papers,
    find_similar_to_new_paper
)

# --------------------------------
# PAGE CONFIGURATION
# --------------------------------

st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🤖",
    layout="wide"
)
# ================================================
# SIDEBAR NAVIGATION
# ================================================

st.sidebar.title("🤖 AI Research Assistant")

st.sidebar.write(
    "Research Intelligence Platform"
)

page = st.sidebar.radio(
    "Navigate",
    [
        "🔎 Paper Search",
        "📊 Research Analytics",
        "📈 Research Trends",
        "👨‍🔬 Author Intelligence",
        "📚 My Bookmarks",
        "➕ Add New Paper",
        "📊 Research Insights"
    ]
)
# --------------------------------
# DATABASE
# --------------------------------

DATABASE = str(Path(__file__).parent / "research_database.db")
# Create bookmarks table if it does not exist
connection = sqlite3.connect(DATABASE)

connection.execute(
    """
    CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE,
        added_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)

connection.commit()
connection.close()


def get_connection():
    return sqlite3.connect(DATABASE)


# Common category data used by multiple pages
connection = get_connection()

category_analytics = pd.read_sql_query(
    """
    SELECT category, COUNT(*) AS paper_count
    FROM papers
    GROUP BY category
    ORDER BY paper_count DESC
    """,
    connection
)

connection.close()



if page == "📊 Research Analytics":
    # ================================================
    # DASHBOARD
    # ================================================

    connection = get_connection()

    total_papers = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM papers",
        connection
    ).iloc[0]["total"]

    category_data = pd.read_sql_query(
        """
        SELECT category, COUNT(*) AS paper_count
        FROM papers
        GROUP BY category
        ORDER BY paper_count DESC
        """,
        connection
    )

    connection.close()


    st.subheader("📊 Research Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "📚 Total Papers",
            f"{total_papers:,}"
        )

    with col2:
        st.metric(
            "🏷️ Categories",
            len(category_data)
        )

    with col3:
        st.metric(
            "🥇 Largest Category",
            category_data.iloc[0]["category"]
        )
    # ================================================
    # RESEARCH ANALYTICS
    # ================================================

    st.divider()

    st.header("📈 Research Analytics")

    connection = get_connection()

    # --------------------------------
    # CATEGORY ANALYTICS
    # --------------------------------

    category_analytics = pd.read_sql_query(
        """
        SELECT category, COUNT(*) AS paper_count
        FROM papers
        GROUP BY category
        ORDER BY paper_count DESC
        """,
        connection
    )

    # --------------------------------
    # PUBLICATION YEAR ANALYTICS
    # --------------------------------

    year_analytics = pd.read_sql_query(
        """
        SELECT published_date, COUNT(*) AS paper_count
        FROM papers
        WHERE published_date IS NOT NULL
        GROUP BY published_date
        ORDER BY published_date
        """,
        connection
    )

    connection.close()


    # Convert dates
    year_analytics["published_date"] = pd.to_datetime(
        year_analytics["published_date"],
        errors="coerce"
    )

    year_analytics = year_analytics.dropna(
        subset=["published_date"]
    )

    year_analytics["year"] = (
        year_analytics["published_date"].dt.year
    )

    year_counts = (
        year_analytics
        .groupby("year")["paper_count"]
        .sum()
        .reset_index()
    )


    # --------------------------------
    # ANALYTICS COLUMNS
    # --------------------------------

    analytics_col1, analytics_col2 = st.columns(2)


    # Category chart
    with analytics_col1:

        st.subheader("🏷️ Papers by Research Category")

        category_chart = category_analytics.set_index(
            "category"
        )

        st.bar_chart(
            category_chart["paper_count"]
        )


    # Year chart
    with analytics_col2:

        st.subheader("📅 Research Papers by Year")

        year_chart = year_counts.set_index("year")

        st.line_chart(
            year_chart["paper_count"]
        )


    # --------------------------------
    # RESEARCH STATISTICS
    # --------------------------------

    st.subheader("📊 Research Statistics")

    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

    with stat_col1:

        st.metric(
            "📚 Total Papers",
            f"{total_papers:,}"
        )

    with stat_col2:

        st.metric(
            "🏷️ Research Categories",
            len(category_analytics)
        )

    with stat_col3:

        st.metric(
            "📈 Research Years",
            len(year_counts)
        )

    with stat_col4:

        average_summary = pd.read_sql_query(
            """
            SELECT AVG(summary_word_count) AS avg_words
            FROM papers
            """,
            get_connection()
        ).iloc[0]["avg_words"]

        st.metric(
            "📝 Avg. Summary Length",
            f"{average_summary:.0f} words"
        )


    # --------------------------------
    # RECENT RESEARCH
    # --------------------------------

    st.subheader("🆕 Recent Research Papers")

    connection = get_connection()

    recent_papers = pd.read_sql_query(
        """
        SELECT title, category, published_date
        FROM papers
        WHERE published_date IS NOT NULL
        ORDER BY published_date DESC
        LIMIT 10
        """,
        connection
    )

    connection.close()

    st.dataframe(
        recent_papers,
        width="stretch",
        hide_index=True
    )
    # ================================================
    # TRENDING RESEARCH TOPICS
    # ================================================

    st.divider()

    st.header("🔥 Trending Research Topics")

    st.write(
        "Discover the most frequently occurring research "
        "terms in the selected research area."
    )

    connection = get_connection()

    # Category selection
    trend_categories = ["All Categories"] + category_analytics[
        "category"
    ].tolist()

    trend_category = st.selectbox(
        "Select research category",
        trend_categories,
        key="trend_category"
    )

    # Number of keywords
    keyword_count = st.slider(
        "Number of topics to display",
        min_value=5,
        max_value=20,
        value=10,
        key="keyword_count"
    )

    # --------------------------------
    # LOAD TITLES
    # --------------------------------

    if trend_category == "All Categories":

        trend_data = pd.read_sql_query(
            """
            SELECT title
            FROM papers
            WHERE title IS NOT NULL
            """,
            connection
        )

    else:

        trend_data = pd.read_sql_query(
            """
            SELECT title
            FROM papers
            WHERE title IS NOT NULL
            AND category = ?
            """,
            connection,
            params=[trend_category]
        )

    connection.close()


    # --------------------------------
    # KEYWORD ANALYSIS
    # --------------------------------


    stop_words = {
        "the", "a", "an", "of", "and", "for",
        "in", "on", "to", "with", "using", "based",
        "from", "by", "via", "is", "are", "as",
        "into", "new", "approach", "method",
        "model", "models", "learning"
    }

    word_counter = Counter()

    for title in trend_data["title"]:

        words = re.findall(
            r"\b[a-zA-Z]{3,}\b",
            title.lower()
        )

        words = [
            word
            for word in words
            if word not in stop_words
        ]

        word_counter.update(words)


    top_topics = word_counter.most_common(
        keyword_count
    )

    topic_df = pd.DataFrame(
        top_topics,
        columns=["Topic", "Frequency"]
    )


    # --------------------------------
    # DISPLAY
    # --------------------------------

    if len(topic_df) > 0:

        trend_col1, trend_col2 = st.columns(2)

        with trend_col1:

            st.subheader("🔥 Most Frequent Topics")

            st.dataframe(
                topic_df,
                width="stretch",
                hide_index=True
            )

        with trend_col2:

            st.subheader("📊 Topic Frequency")

            topic_chart = topic_df.set_index(
                "Topic"
            )

            st.bar_chart(
                topic_chart["Frequency"]
            )

    else:

        st.info(
            "No research topics could be extracted."
        )
    # ================================================

elif page == "🔎 Paper Search":
    # PAPER SEARCH
    # ================================================

    st.divider()

    st.header("🔎 Search Research Papers")

    search_text = st.text_input(
        "Search by paper title",
        placeholder="Example: machine learning, neural network, robotics..."
    )


    # ================================================
    # Load categories for the search filter
    connection = get_connection()
    category_data = pd.read_sql_query(
        "SELECT category FROM papers GROUP BY category ORDER BY category",
        connection
    )
    connection.close()

    # CATEGORY FILTER
    # ================================================

    categories = ["All Categories"] + category_data["category"].tolist()

    selected_category = st.selectbox(
        "Filter by category",
        categories
    )


    # ================================================
    # BUILD SEARCH QUERY
    # ================================================
    connection = get_connection()

    query = """
    SELECT *
    FROM papers
    WHERE 1 = 1
    """

    parameters = []

    # Title search
    if search_text:
        query += " AND title LIKE ?"
        parameters.append(f"%{search_text}%")

    # Category filter
    if selected_category != "All Categories":
        query += " AND category = ?"
        parameters.append(selected_category)
    query += " LIMIT 50"

    papers = pd.read_sql_query(
        query,
        connection,
        params=parameters
    )

    connection.close()


    # ================================================
    # DISPLAY RESULTS
    # ================================================

    st.subheader("📚 Search Results")

    st.write(
        f"Found **{len(papers)} papers**"
    )

    if len(papers) > 0:

        # Display titles and categories
        display_columns = [
            "title",
            "category"
        ]

        st.dataframe(
            papers[display_columns],
            width="stretch",
            hide_index=True
        )

    else:

        st.warning(
            "No papers found. Try a different search."
        )


    # ================================================
    # PAPER DETAILS
    # ================================================

    if len(papers) > 0:

        st.divider()

        st.subheader("📖 View Paper Details")

        paper_titles = papers["title"].tolist()

        selected_paper = st.selectbox(
            "Select a paper",
            paper_titles
        )

        selected_row = papers[
            papers["title"] == selected_paper
        ].iloc[0]

        st.markdown(
            f"### {selected_row['title']}"
        )

        st.write(
            f"**Category:** {selected_row['category']}"
        )
        # --------------------------------
        # BOOKMARK PAPER
        # --------------------------------
    
        if st.button("⭐ Bookmark This Paper"):
    
            connection = get_connection()
    
            try:
    
                connection.execute(
                    """
                    INSERT INTO bookmarks (title)
                    VALUES (?)
                    """,
                    (selected_row["title"],)
                )
    
                connection.commit()
    
                st.success("⭐ Paper added to your bookmarks!")
    
            except sqlite3.IntegrityError:
    
                st.info("⭐ This paper is already bookmarked.")
    
            connection.close()

        # Show summary if available
        if "summary" in papers.columns:

            st.markdown("#### 📝 Summary")

            st.write(selected_row["summary"])

        # ================================================
        # PAPER INTELLIGENCE
        # ================================================
    
        st.markdown("#### 🧠 Paper Intelligence")
    
        # --------------------------------
        # BASIC PAPER INFORMATION
        # --------------------------------
    
        info_col1, info_col2, info_col3 = st.columns(3)
    
        with info_col1:
    
            st.metric(
                "📝 Summary Length",
                f"{selected_row['summary_word_count']} words"
            )
    
        with info_col2:
    
            st.metric(
                "🏷️ Category",
                selected_row["category"]
            )
    
        with info_col3:
    
            publication_date = selected_row.get(
                "published_date",
                "N/A"
            )
    
            st.metric(
                "📅 Published",
                str(publication_date)[:10]
            )
    
    
        # --------------------------------
        # AUTHORS
        # --------------------------------
    
        if "authors" in papers.columns:
    
            st.markdown("#### 👨‍🔬 Authors")
    
            st.write(
                selected_row["authors"]
            )
    
    
        # --------------------------------
        # KEYWORD EXTRACTION
        # --------------------------------
    
        st.markdown("#### 🔑 Key Research Terms")
    
        from collections import Counter
        import re
    
        text = (
            str(selected_row["title"])
            + " "
            + str(selected_row["summary"])
        ).lower()
    
        words = re.findall(
            r"\b[a-zA-Z]{4,}\b",
            text
        )
    
        stop_words = {
            "this", "that", "with", "from",
            "using", "based", "which", "into",
            "their", "these", "have", "been",
            "were", "also", "than", "such",
            "between", "through", "more",
            "other", "paper", "proposed",
            "approach", "method", "methods",
            "model", "models", "using",
            "results", "show", "shows"
        }
    
        keywords = [
            word
            for word in words
            if word not in stop_words
        ]
    
        keyword_counts = Counter(keywords)
    
        top_keywords = keyword_counts.most_common(10)
    
        keyword_df = pd.DataFrame(
            top_keywords,
            columns=["Keyword", "Frequency"]
        )
    
        if len(keyword_df) > 0:
    
            keyword_col1, keyword_col2 = st.columns(2)
    
            with keyword_col1:
    
                st.dataframe(
                    keyword_df,
                    width="stretch",
                    hide_index=True
                )
    
            with keyword_col2:
    
                st.bar_chart(
                    keyword_df.set_index(
                        "Keyword"
                    )["Frequency"]
                )
        # ================================================
        # SIMILAR RESEARCH PAPERS
        # ================================================
    
        st.divider()
    
        st.subheader("🔎 Similar Research Papers")
    
        with st.spinner("Finding similar research papers..."):
    
            similar_papers = find_similar_papers(
                selected_paper,
                5
            )
    
        if similar_papers.empty:
    
            st.info("No similar papers found.")
    
        else:
    
            for _, paper in similar_papers.iterrows():
    
                st.markdown(f"### 📄 {paper['title']}")
    
                st.write(
                    f"**Category:** {paper['category']}"
                )
    
                st.write(
                    f"**Similarity:** {paper['similarity_score']}%"
                )
    
                st.divider()
        # ================================================
        # PAPER COMPARISON
        # ================================================
    
        st.divider()
    
        st.header("📚 Compare Research Papers")
    
        comparison_papers = st.multiselect(
            "Select exactly 2 papers",
            papers["title"].tolist(),
            max_selections=2
        )
    
        if len(comparison_papers) == 2:
    
            paper_1 = papers[
                papers["title"] == comparison_papers[0]
            ].iloc[0]
    
            paper_2 = papers[
                papers["title"] == comparison_papers[1]
            ].iloc[0]
    
            st.success("✅ Two papers selected!")
    
            if st.button("🔍 Compare Papers"):
    
                st.subheader("🤖 AI Research Paper Comparison")
    
                try:
                    with st.spinner("🧠 Gemini is analyzing the two papers..."):
                        comparison_result = compare_papers(
                            paper_1["summary"],
                            paper_2["summary"]
                        )
                    st.markdown(comparison_result)
                except Exception as error:
                    st.error(
                        "⚠️ Could not get the AI comparison. Check that "
                        "GEMINI_API_KEY is set in your secrets and try again."
                    )
                    st.caption(f"Details: {error}")
    
        else:
            st.info("👆 Please select exactly 2 papers.")
            # ================================================
    
elif page == "📈 Research Trends":
    # RESEARCH TREND EVOLUTION
    # ================================================

    st.divider()
    st.header("📈 Research Trend Evolution")
    st.write(
        "Analyze how research activity has changed over time "
        "across different research categories."
    )

    connection = get_connection()

    trend_data = pd.read_sql_query(
        """
        SELECT category, published_date
        FROM papers
        WHERE category IS NOT NULL
        AND published_date IS NOT NULL
        """,
        connection
    )

    connection.close()

    # Convert publication date
    trend_data["published_date"] = pd.to_datetime(
        trend_data["published_date"],
        errors="coerce"
    )

    trend_data = trend_data.dropna(
        subset=["published_date"]
    )

    trend_data["Year"] = (
        trend_data["published_date"].dt.year
    )

    # --------------------------------
    # CATEGORY SELECTION
    # --------------------------------

    trend_category_options = [
        "All Categories"
    ] + sorted(
        trend_data["category"].unique().tolist()
    )

    selected_trend_category = st.selectbox(
        "🏷️ Select Research Category",
        trend_category_options,
        key="research_trend_category"
    )

    # --------------------------------
    # FILTER DATA
    # --------------------------------

    if selected_trend_category == "All Categories":

        yearly_trend = (
            trend_data
            .groupby("Year")
            .size()
            .reset_index(name="Paper Count")
        )

    else:

        filtered_trend = trend_data[
            trend_data["category"]
            == selected_trend_category
        ]

        yearly_trend = (
            filtered_trend
            .groupby("Year")
            .size()
            .reset_index(name="Paper Count")
        )

    # --------------------------------
    # TREND CHART
    # --------------------------------

    if len(yearly_trend) > 0:

        st.subheader("📊 Publication Trend")

        st.line_chart(
            yearly_trend.set_index("Year")["Paper Count"]
        )

        # --------------------------------
        # TREND STATISTICS
         # --------------------------------
        # TREND STATISTICS
        # --------------------------------

        total_category_papers = yearly_trend["Paper Count"].sum()

        peak_year_row = yearly_trend.loc[
            yearly_trend["Paper Count"].idxmax()
        ]

        peak_year = int(peak_year_row["Year"])
        peak_year_count = int(peak_year_row["Paper Count"])

        stat_col1, stat_col2, stat_col3 = st.columns(3)

        with stat_col1:
            st.metric(
                "📚 Total Papers",
                f"{int(total_category_papers):,}"
            )

        with stat_col2:
            st.metric(
                "🏆 Peak Research Year",
                peak_year
            )

        with stat_col3:
            st.metric(
                "🔥 Papers in Peak Year",
                f"{peak_year_count:,}"
            )

        # --------------------------------
        # YEARLY DATA
        # --------------------------------

        st.subheader("📋 Year-wise Research Activity")

        st.dataframe(
            yearly_trend,
            width="stretch",
            hide_index=True
        )

    else:

        st.info(
            "No publication trend data available "
            "for the selected category."
        )
        # ================================================
    # EMERGING RESEARCH AREAS
    # ================================================

    st.divider()

    st.header("🚀 Emerging Research Areas")

    st.write(
        "Identify research categories with strong publication activity "
        "in the latest available years."
    )

    connection = get_connection()

    emerging_data = pd.read_sql_query(
        """
        SELECT category, published_date
        FROM papers
        WHERE category IS NOT NULL
        AND published_date IS NOT NULL
        """,
        connection
    )

    connection.close()

    emerging_data["published_date"] = pd.to_datetime(
        emerging_data["published_date"],
        errors="coerce"
    )

    emerging_data = emerging_data.dropna(
        subset=["published_date"]
    )

    emerging_data["Year"] = (
        emerging_data["published_date"].dt.year
    )

    if len(emerging_data) > 0:

        latest_year = int(
            emerging_data["Year"].max()
        )

        recent_data = emerging_data[
            emerging_data["Year"] >= latest_year - 2
        ]

        emerging_categories = (
            recent_data
            .groupby("category")
            .size()
            .reset_index(name="Recent Papers")
            .sort_values(
                "Recent Papers",
                ascending=False
            )
            .head(10)
        )

        st.subheader(
            f"🔥 Most Active Research Areas "
            f"({latest_year - 2}–{latest_year})"
        )

        emerging_col1, emerging_col2 = st.columns(2)

        with emerging_col1:

            st.dataframe(
                emerging_categories,
                width="stretch",
                hide_index=True
            )

        with emerging_col2:

            st.bar_chart(
                emerging_categories.set_index(
                    "category"
                )["Recent Papers"]
            )

    else:

        st.info(
            "No research trend data available."
        )

elif page == "👨‍🔬 Author Intelligence":
    # AUTHOR INTELLIGENCE
    # ================================================

    st.divider()

    st.header("👨‍🔬 Author Intelligence")

    st.write(
        "Explore researchers, their publication activity, "
        "and the research areas they contribute to."
    )

    connection = get_connection()

    # --------------------------------
    # LOAD AUTHORS
    # --------------------------------

    author_data = pd.read_sql_query(
        """
        SELECT authors, title, category, published_date
        FROM papers
        WHERE authors IS NOT NULL
        AND authors != ''
        """,
        connection
    )

    connection.close()


    # --------------------------------
    # EXTRACT INDIVIDUAL AUTHORS
    # --------------------------------

    from collections import Counter

    author_counter = Counter()

    for authors in author_data["authors"]:

        # arXiv authors are generally separated by commas
        author_list = [
            author.strip()
            for author in str(authors).split(",")
            if author.strip()
        ]

        for author in author_list:
            author_counter[author] += 1


    # --------------------------------
    # TOP AUTHORS
    # --------------------------------

    top_authors = author_counter.most_common(15)

    top_author_df = pd.DataFrame(
        top_authors,
        columns=["Author", "Paper Count"]
    )


    # --------------------------------
    # DISPLAY TOP AUTHORS
    # --------------------------------

    author_col1, author_col2 = st.columns(2)

    with author_col1:

        st.subheader("🏆 Most Active Researchers")

        st.dataframe(
            top_author_df,
            width="stretch",
            hide_index=True
        )


    with author_col2:

        st.subheader("📊 Publication Activity")

        author_chart = top_author_df.set_index(
            "Author"
        )

        st.bar_chart(
            author_chart["Paper Count"]
        )


    # --------------------------------
    # AUTHOR SEARCH
    # --------------------------------

    st.subheader("🔎 Explore a Researcher")

    author_names = [
        author
        for author, count in top_authors
    ]

    selected_author = st.selectbox(
        "Select a researcher",
        author_names,
        key="selected_author"
    )


    # --------------------------------
    # SELECTED AUTHOR PAPERS
    # --------------------------------

    if selected_author:

        connection = get_connection()

        selected_author_papers = pd.read_sql_query(
            """
            SELECT title, category, published_date
            FROM papers
            WHERE authors LIKE ?
            ORDER BY published_date DESC
            """,
            connection,
            params=[f"%{selected_author}%"]
        )

        connection.close()

        st.write(
            f"### 📚 Papers by {selected_author}"
        )

        st.metric(
            "Total Papers Found",
            len(selected_author_papers)
        )

        if len(selected_author_papers) > 0:

            st.dataframe(
                selected_author_papers,
                width="stretch",
                hide_index=True
            )

            # --------------------------------
            # AUTHOR CATEGORIES
            # --------------------------------

            st.subheader(
                "🏷️ Research Areas"
            )

            author_categories = (
                selected_author_papers["category"]
                .value_counts()
                .reset_index()
            )

            author_categories.columns = [
                "Category",
                "Paper Count"
            ]

            st.bar_chart(
                author_categories.set_index(
                    "Category"
                )["Paper Count"]
            )

        else:

            st.info(
                "No papers found for this researcher."
            )
            # ================================================

elif page == "➕ Add New Paper":
    # ADD NEW PAPER & ANALYZE
    # ================================================

    st.divider()
    st.header("➕ Add & Analyze a Research Paper")
    st.write("Enter a new research paper to analyze its content and find similar research.")

    new_title = st.text_input(
        "📄 Paper Title",
        placeholder="Enter the research paper title"
    )

    new_summary = st.text_area(
        "📝 Paper Abstract / Summary",
        placeholder="Enter the abstract or summary of the research paper",
        height=180
    )

    new_authors = st.text_input(
        "👨‍🔬 Authors",
        placeholder="Example: John Smith, Alice Brown"
    )

    new_category = st.selectbox(
        "🏷️ Research Category",
        category_analytics["category"].tolist(),
        key="new_paper_category"
    )

    if st.button("🧠 Analyze New Paper"):

        if not new_title or not new_summary:

            st.warning("⚠️ Please enter both the paper title and summary.")

        else:

            st.success("✅ Paper information received!")

            # --------------------------------
            # BASIC ANALYSIS
            # --------------------------------

            st.subheader("📊 Paper Analysis")

            word_count = len(
                new_summary.split()
            )

            analysis_col1, analysis_col2, analysis_col3 = st.columns(3)

            with analysis_col1:
                st.metric(
                    "📝 Summary Words",
                    word_count
                )

            with analysis_col2:
                st.metric(
                    "🏷️ Category",
                    new_category
                )

            with analysis_col3:
                st.metric(
                    "🔤 Title Words",
                    len(new_title.split())
                )

            # --------------------------------
            # KEYWORD EXTRACTION
            # --------------------------------

            st.subheader("🔑 Extracted Keywords")

            from collections import Counter
            import re

            combined_text = (
                new_title + " " + new_summary
            ).lower()

            words = re.findall(
                r"\b[a-zA-Z]{4,}\b",
                combined_text
            )

            stop_words_new = {
                "this", "that", "with", "from",
                "using", "based", "which", "into",
                "their", "these", "have", "been",
                "were", "also", "than", "such",
                "between", "through", "more",
                "other", "paper", "proposed",
                "approach", "method", "methods",
                "model", "models", "results",
                "show", "shows"
            }

            keywords = [
                word
                for word in words
                if word not in stop_words_new
            ]

            keyword_counts = Counter(keywords)

            top_new_keywords = keyword_counts.most_common(10)

            new_keyword_df = pd.DataFrame(
                top_new_keywords,
                columns=["Keyword", "Frequency"]
            )

            if len(new_keyword_df) > 0:

                new_col1, new_col2 = st.columns(2)

                with new_col1:
                    st.dataframe(
                        new_keyword_df,
                        width="stretch",
                        hide_index=True
                    )

                with new_col2:
                    st.bar_chart(
                        new_keyword_df.set_index(
                            "Keyword"
                        )["Frequency"]
                    )

            # --------------------------------
            # SIMILAR PAPERS USING TF-IDF
            # --------------------------------

            st.subheader("🔎 Similar Existing Research")

            with st.spinner("🤖 Finding similar research papers..."):

                similar_new_papers = find_similar_to_new_paper(
                    new_title,
                    new_summary,
                    5
                )

            if similar_new_papers.empty:

                st.info("No similar papers found.")

            else:

                st.success(
                    "✅ Similar research papers identified!"
                )

                for _, paper in similar_new_papers.iterrows():

                    st.markdown(
                        f"### 📄 {paper['title']}"
                    )

                    st.write(
                        f"**Category:** {paper['category']}"
                    )

                    st.write(
                        f"**Similarity:** "
                        f"{paper['similarity_score']}%"
                    )

                    st.divider()

elif page == "📚 My Bookmarks":
    # ================================================
    # MY BOOKMARKS
    # ================================================

    st.divider()
    st.header("📚 My Bookmarks")

    st.write(
        "View and manage your saved research papers."
    )

    connection = get_connection()

    bookmarked_papers = pd.read_sql_query(
        """
        SELECT title, added_on
        FROM bookmarks
        ORDER BY added_on DESC
        """,
        connection
    )

    connection.close()

    if len(bookmarked_papers) > 0:

        st.success(
            f"⭐ You have {len(bookmarked_papers)} bookmarked paper(s)."
        )

        for _, bookmark in bookmarked_papers.iterrows():

            col1, col2 = st.columns([5, 1])

            with col1:
                st.write(
                    f"📄 **{bookmark['title']}**"
                )
                st.caption(
                    f"Saved on: {bookmark['added_on']}"
                )

            with col2:

                if st.button(
                    "🗑️ Remove",
                    key=f"remove_{bookmark['title']}"
                ):

                    connection = get_connection()

                    connection.execute(
                        "DELETE FROM bookmarks WHERE title = ?",
                        (bookmark["title"],)
                    )

                    connection.commit()
                    connection.close()

                    st.success("Bookmark removed!")

                    st.rerun()

    else:

        st.info(
            "📭 No bookmarked papers yet. "
            "Use the ⭐ Bookmark This Paper button to save one."
        )

elif page == "📊 Research Insights":
        # ================================================
    # RESEARCH INSIGHTS DASHBOARD
    # ================================================

    st.divider()
    st.header("📊 Research Insights Dashboard")

    st.write(
        "A consolidated overview of the research database."
    )

    connection = get_connection()

    dashboard_data = pd.read_sql_query(
        """
        SELECT category, published_date
        FROM papers
        WHERE category IS NOT NULL
        """,
        connection
    )

    connection.close()

    dashboard_data["published_date"] = pd.to_datetime(
        dashboard_data["published_date"],
        errors="coerce"
    )

    dashboard_data["Year"] = (
        dashboard_data["published_date"].dt.year
    )

    # --------------------------------
    # KPI CALCULATIONS
    # --------------------------------

    dashboard_total = len(dashboard_data)

    dashboard_categories = (
        dashboard_data["category"].nunique()
    )

    dashboard_years = (
        dashboard_data["Year"].nunique()
    )

    dashboard_latest_year = (
        int(dashboard_data["Year"].max())
        if dashboard_data["Year"].notna().any()
        else "N/A"
    )

    # --------------------------------
    # KPI CARDS
    # --------------------------------

    dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)

    with dash_col1:
        st.metric(
            "📚 Total Papers",
            f"{dashboard_total:,}"
        )

    with dash_col2:
        st.metric(
            "🏷️ Categories",
            dashboard_categories
        )

    with dash_col3:
        st.metric(
            "📅 Research Years",
            dashboard_years
        )

    with dash_col4:
        st.metric(
            "🆕 Latest Year",
            dashboard_latest_year
        )
       # ================================================
    # RESEARCH ANALYTICS DASHBOARD
    # ================================================

    st.subheader("📊 Research Analytics Dashboard")

    connection = get_connection()

    # ================================================
    # 1. KPI DATA
    # ================================================

    # Total Papers
    total_papers = pd.read_sql_query(
        """
        SELECT COUNT(*) AS total
        FROM papers
        """,
        connection
    ).iloc[0]["total"]


    # Total Categories
    total_categories = pd.read_sql_query(
        """
        SELECT COUNT(DISTINCT category) AS total
        FROM papers
        WHERE category IS NOT NULL
        """,
        connection
    ).iloc[0]["total"]


    # Total Publication Years
    total_years = pd.read_sql_query(
        """
        SELECT COUNT(DISTINCT strftime('%Y', published_date)) AS total
        FROM papers
        WHERE published_date IS NOT NULL
        """,
        connection
    ).iloc[0]["total"]


    # Author Data
    author_dashboard = pd.read_sql_query(
        """
        SELECT authors
        FROM papers
        WHERE authors IS NOT NULL
        """,
        connection
    )


    # ================================================
    # 2. COUNT UNIQUE AUTHORS
    # ================================================

    unique_authors = set()

    for author_string in author_dashboard["authors"]:

        if pd.notna(author_string):

            authors_list = str(author_string).split(",")

            for author in authors_list:

                author = author.strip()

                if author:
                    unique_authors.add(author)


    total_authors = len(unique_authors)


    connection.close()


    # ================================================
    # 3. KPI CARDS
    # ================================================

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)


    with kpi1:

        st.metric(
            label="📚 Total Papers",
            value=f"{int(total_papers):,}"
        )


    with kpi2:

        st.metric(
            label="👨‍🔬 Total Authors",
            value=f"{total_authors:,}"
        )


    with kpi3:

        st.metric(
            label="🏷️ Research Categories",
            value=f"{int(total_categories):,}"
        )


    with kpi4:

        st.metric(
            label="📅 Publication Years",
            value=f"{int(total_years):,}"
        )


    st.divider()


    # ================================================
    # 4. PAPERS BY CATEGORY
    # ================================================

    connection = get_connection()

    category_dashboard = pd.read_sql_query(
        """
        SELECT category, COUNT(*) AS paper_count
        FROM papers
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY paper_count DESC
        """,
        connection
    )


    # ================================================
    # 5. PUBLICATION TREND
    # ================================================

    year_dashboard = pd.read_sql_query(
        """
        SELECT published_date
        FROM papers
        WHERE published_date IS NOT NULL
        """,
        connection
    )


    connection.close()


    # ================================================
    # 6. PREPARE YEAR DATA
    # ================================================

    year_dashboard["published_date"] = pd.to_datetime(
        year_dashboard["published_date"],
        errors="coerce"
    )

    year_dashboard = year_dashboard.dropna(
        subset=["published_date"]
    )

    year_dashboard["Year"] = (
        year_dashboard["published_date"].dt.year
    )


    year_counts = (
        year_dashboard
        .groupby("Year")
        .size()
        .reset_index(name="Paper Count")
    )


    # ================================================
    # 7. PREPARE TOP AUTHORS
    # ================================================

    all_authors = []

    for author_string in author_dashboard["authors"]:

        if pd.notna(author_string):

            authors_list = str(author_string).split(",")

            for author in authors_list:

                author = author.strip()

                if author:
                    all_authors.append(author)


    if all_authors:

        top_authors = (
            pd.Series(all_authors)
            .value_counts()
            .head(10)
            .reset_index()
        )

        top_authors.columns = [
            "Author",
            "Publications"
        ]

    else:

        top_authors = pd.DataFrame(
            columns=["Author", "Publications"]
        )
    # ================================================
    # DASHBOARD CHARTS
    # ================================================

    st.subheader("📊 Research Analytics")

    connection = get_connection()

    # --------------------------------
    # 1. PAPERS BY CATEGORY
    # --------------------------------

    category_dashboard = pd.read_sql_query(
        """
        SELECT category, COUNT(*) AS paper_count
        FROM papers
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY paper_count DESC
        """,
        connection
    )

    # --------------------------------
    # 2. PUBLICATION TREND
    # --------------------------------

    year_dashboard = pd.read_sql_query(
        """
        SELECT published_date
        FROM papers
        WHERE published_date IS NOT NULL
        """,
        connection
    )

    # --------------------------------
    # 3. TOP AUTHORS
    # --------------------------------

    author_dashboard = pd.read_sql_query(
        """
        SELECT authors
        FROM papers
        WHERE authors IS NOT NULL
        """,
        connection
    )

    connection.close()


    # ================================================
    # PREPARE YEAR DATA
    # ================================================

    year_dashboard["published_date"] = pd.to_datetime(
        year_dashboard["published_date"],
        errors="coerce"
    )

    year_dashboard = year_dashboard.dropna(
        subset=["published_date"]
    )

    year_dashboard["Year"] = (
        year_dashboard["published_date"].dt.year
    )

    year_counts = (
        year_dashboard
        .groupby("Year")
        .size()
        .reset_index(name="Paper Count")
    )


    # ================================================
    # PREPARE AUTHOR DATA
    # ================================================

    all_authors = []

    for author_string in author_dashboard["authors"]:

        if pd.notna(author_string):

            authors_list = str(author_string).split(",")

            for author in authors_list:

                author = author.strip()

                if author:
                    all_authors.append(author)

    top_authors = (
        pd.Series(all_authors)
        .value_counts()
        .head(10)
        .reset_index()
    )

    top_authors.columns = [
        "Author",
        "Publications"
    ]


    # ================================================
    # DISPLAY CHARTS
    # ================================================

    chart_col1, chart_col2 = st.columns(2)


    # --------------------------------
    # CATEGORY CHART
    # --------------------------------

    with chart_col1:

        st.write("### 🏷️ Papers by Research Category")

        st.bar_chart(
            category_dashboard.set_index(
                "category"
            )["paper_count"]
        )


    # --------------------------------
    # YEAR TREND
    # --------------------------------

    with chart_col2:

        st.write("### 📈 Publication Trend")

        st.line_chart(
            year_counts.set_index(
                "Year"
            )["Paper Count"]
        )


    # ================================================
    # TOP AUTHORS
    # ================================================

    st.write("### 👨‍🔬 Top Research Authors")

    st.bar_chart(
        top_authors.set_index(
            "Author"
        )["Publications"]
    )

    st.dataframe(
        top_authors,
        width="stretch",
        hide_index=True
    )
    # ================================================
    # POWER BI DATA EXPORT
    # ================================================

    st.divider()
    st.header("📊 Power BI Dataset")

    st.write(
        "Export the research database as a CSV file "
        "for Power BI analysis and dashboard creation."
    )

    connection = get_connection()

    powerbi_data = pd.read_sql_query(
        """
        SELECT
            title,
            category,
            published_date,
            authors,
            summary,
            summary_word_count
        FROM papers
        """,
        connection
    )

    connection.close()

    # Convert publication date
    powerbi_data["published_date"] = pd.to_datetime(
        powerbi_data["published_date"],
        errors="coerce"
    )

    # Add year column
    powerbi_data["Year"] = (
        powerbi_data["published_date"].dt.year
    )

    # Download button
    csv_data = powerbi_data.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="⬇️ Download Power BI Dataset",
        data=csv_data,
        file_name="powerbi_research_data.csv",
        mime="text/csv"
    )

    st.success(
        f"Power BI dataset ready — "
        f"{len(powerbi_data):,} research papers."
    )
