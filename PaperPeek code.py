# -*- coding: utf-8 -*-


import os
import json
import chardet
import numpy as np
import pandas as pd
import re
import math
import string
import random
import xml.etree.ElementTree as ET
from google.colab import drive
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize, sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from transformers import AutoModel, AutoTokenizer




nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

# Step 1: Mount Google Drive
drive.mount('/content/drive')

# Set the path to the dataset folder
dataset_path = '/content/drive/My Drive/IRdataset'  # Adjust the path according to your Google Drive structure

# Debugging function to just return the file path
def debug_process_file(file_path):
    return file_path  # Just return the file path for debugging

# Initialize an empty list to store data
data = []

# Step 2: Traverse the directories and debug file paths
for root, dirs, files in os.walk(dataset_path):
    for file in files:
        file_path = os.path.join(root, file)
        file_data = debug_process_file(file_path)

        # Debugging: Print the file path
        print("Processing file:", file_path)

        # Add the file path to the data list
        data.append({'file_path': file_data})

# Step 3: Create DataFrame
df = pd.DataFrame(data)

# Display the first few rows of the DataFrame
print(df.head())

"""### File encoding"""

# Function to detect file encoding
def get_file_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    return chardet.detect(raw_data)['encoding']

# Function to process XML file
def process_xml(file_path):
    # Parse the XML file
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Extract all text within the XML file
    all_text = []
    for elem in root.iter():
        if elem.text:
            all_text.append(elem.text.strip())

    return ' '.join(all_text)

# Function to process a single file based on its type
def process_file(file_path, file_type):
    # Detect encoding and read the file
    encoding = get_file_encoding(file_path)
    with open(file_path, 'r', encoding=encoding) as f:
        if file_type == 'json':
            return json.load(f)
        elif file_type == 'txt':
            return f.read()
        elif file_type == 'xml':
            return process_xml(file_path)
        else:
            return None



# Initialize a dictionary to store data
data = {}

# Step 2: Traverse the directories and process files
for root, dirs, files in os.walk(dataset_path):
    parts = root.split(os.sep)
    if len(parts) > parts.index('IRdataset') + 1:   #change the dataset name if applies
        folder_name = parts[parts.index('IRdataset') + 1]
    else:
        continue  # Skip the root directory

    if folder_name not in data:
        data[folder_name] = {'citation': None, 'summary': None, 'document': None}

    for file in files:
        file_path = os.path.join(root, file)

        # Determine the type of file and process accordingly
        if file.endswith('.json'):
            file_content = process_file(file_path, 'json')
            data[folder_name]['citation'] = file_content
        elif file.endswith('.txt') and 'summary' in root:
            file_content = process_file(file_path, 'txt')
            data[folder_name]['summary'] = file_content
        elif file.endswith('.xml') and 'Documents_xml' in root:
            file_content = process_file(file_path, 'xml')
            data[folder_name]['document'] = file_content

# Convert the dictionary to a DataFrame
df = pd.DataFrame.from_dict(data, orient='index').reset_index().rename(columns={'index': 'folder_name'})

# Display the first few rows of the DataFrame
print(df.head())

"""Processed data CSV"""

def extract_paper_name(summary):
    # Split the summary by new line and return the first line
    return summary.split('\n')[0]

df['paper_name'] = df['summary'].apply(extract_paper_name)

print(df['citation'].to_string(index=False))

# First, ensure you have a consistent structure for all rows. If not, you need to preprocess it to make it consistent.
# Now, create separate columns
keys = ['citance_No', 'citing_paper_id', 'citing_paper_authority', 'citing_paper_authors', 'raw_text', 'clean_text', 'keep_for_gold']
for key in keys:
    # Apply a function to extract the value for each key in the citation dictionaries
    df[key] = df['citation'].apply(lambda citations: [citation.get(key, None) for citation in citations])

# At this point, each of the new columns will contain lists of values

"""Weighted score calculation"""

def calculate_weighted_score(citations):
    weighted_scores = [
        citation['citing_paper_authority'] * (0.5 if citation['keep_for_gold'] == 0 else 1)
        for citation in citations
    ]
    total_weighted_score = sum(weighted_scores)
    return total_weighted_score

# Apply the scoring function to each row's 'citation' column to create a new 'weighted_score' column
df['weighted_score'] = df['citation'].apply(calculate_weighted_score)

# Find the maximum weighted score for normalization
max_weighted_score = df['weighted_score'].max()

# Avoid division by zero in case max_weighted_score is zero
if max_weighted_score == 0:
    df['normalized_score'] = 0
else:
    # Normalize the scores to the range [0, 1]
    df['normalized_score'] = df['weighted_score'] / max_weighted_score

"""citation count"""

# Define a function to extract the maximum citance_No as the citation count
def extract_citation_count(citance_no_list):
    if not citance_no_list:  # Check if the list is empty
        return 0
    return max(citance_no_list)

# Apply the function to the 'citance_No' column to create a new 'citation_count' column
df['citation_count'] = df['citance_No'].apply(extract_citation_count)

print(df.head())

"""# Data preprocessing"""

def preprocess_text(text):
    # Sentence Tokenization
    sentences = sent_tokenize(text)

    processed_sentences = []
    for sentence in sentences:
        # Tokenization
        tokens = word_tokenize(sentence)

        # Case Normalization
        tokens = [token.lower() for token in tokens]

        # Removing Punctuation and Special Characters
        tokens = [token for token in tokens if token.isalnum()]

        # Removing Stop Words
        stop_words = set(stopwords.words('english'))
        tokens = [word for word in tokens if word not in stop_words]

        # Stemming/Lemmatization
        lemmatizer = WordNetLemmatizer()
        tokens = [lemmatizer.lemmatize(token) for token in tokens]

        # Reconstruct the sentence
        processed_sentence = ' '.join(tokens)
        processed_sentences.append(processed_sentence)

    # Return the processed text
    return ' '.join(processed_sentences)

df['processed_summary'] = df['summary'].apply(preprocess_text)
df['processed_document'] = df['document'].apply(preprocess_text)

"""NEW dataframe with chosen columns"""

# Selecting specific columns to create a new DataFrame
new_df = df[['processed_document', 'processed_summary', 'normalized_score', 'citation_count','paper_name']].copy()
new_df['index'] = new_df.index

# Display the first few rows of the new DataFrame to verify
print(new_df.head())
new_df

"""# First level retrieval"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.metrics.pairwise import cosine_similarity

"""

Tf-idf and then LDA to have more unique topic modeling.

"""

def apply_tfidf_and_lda(dataframe,  document_col, n_topics_document=10):
    # Initialize TfidfVectorizers

    tfidf_vectorizer_document = TfidfVectorizer(max_df=0.95, min_df=2, stop_words='english')

    # Fit and transform the text data with TfidfVectorizer

    tfidf_document = tfidf_vectorizer_document.fit_transform(dataframe[document_col])

    # Initialize LDA models
    lda_document = LatentDirichletAllocation(n_components=n_topics_document, random_state=0)

    # Fit LDA models on TF-IDF transformed data

    lda_document.fit(tfidf_document)

    return lda_document, tfidf_vectorizer_document

# Using the function
# lda_document_model, tfidf_vectorizer_document = apply_tfidf_and_lda(new_df,  'processed_document')

"""Function to display the topics"""

def display_topics(model, feature_names, no_top_words, no_top_topics=None):
    """
    Display the top words for each topic from an LDA model.

    :param model: The fitted LDA model.
    :param feature_names: The feature names (words) from the vectorizer.
    :param no_top_words: The number of top words to display for each topic.
    :param no_top_topics: (Optional) The number of topics to display. If None, display all topics.
    """
    for topic_idx, topic in enumerate(model.components_):
        if no_top_topics is not None and topic_idx >= no_top_topics:
            break
        print(f"Topic {topic_idx}:")
        print(" ".join([feature_names[i] for i in topic.argsort()[:-no_top_words - 1:-1]]))

lda_document_model, tfidf_vectorizer_document = apply_tfidf_and_lda(new_df,  'processed_document')

# Display topics for document LDA model
print("\nTopics in Documents:")
display_topics(lda_document_model, tfidf_vectorizer_document.get_feature_names_out(), 10)

"""First level document retrieval(top "n" documents)"""

def top_n_papers_refined(query, lda_model, dtm, dataframe, vectorizer, citation_col, normalized_col, preprocess_function, n=20, similarity_weight=0.6, citation_weight=0.3, normalized_weight=0.1):
    """Retrieves the top n papers based on a weighted combination of LDA topic similarity, citation scores, and normalized scores.
    :param lda_model: The trained LDA model.
    :param dtm: Document-term matrix of the papers.
    :param dataframe: DataFrame containing the papers with citation and normalized score columns.
    :param vectorizer: The vectorizer used to transform the original documents for the LDA model.
    :param citation_col: Name of the column in the DataFrame for citation scores.
    :param normalized_col: Name of the column in the DataFrame for normalized scores.
    :param preprocess_function: Function to preprocess the user query.
    :param n: Number of top papers to return.
    :param similarity_weight: Weight for the LDA topic similarity score.
    :param citation_weight: Weight for the citation score.
    :param normalized_weight: Weight for the normalized score.
    :return: DataFrame of the top n papers with scores and rankings.
    """
    # Get user query
    processed_query = preprocess_function(query)

    # Transform the query to match the same feature space as the LDA model
    query_transformed = lda_model.transform(vectorizer.transform([processed_query]))

    # Calculate similarity scores between the query and each document
    topic_similarities = cosine_similarity(query_transformed, lda_model.transform(dtm)).flatten()

    # Create a combined score
    combined_scores = (similarity_weight * topic_similarities) + \
                      (citation_weight * dataframe[citation_col]) + \
                      (normalized_weight * dataframe[normalized_col])

    # Add combined score to the DataFrame
    dataframe['combined_score'] = combined_scores

    # Sort the DataFrame based on the combined score
    top_papers = dataframe.sort_values(by='combined_score', ascending=False).head(n)

    return top_papers

#document-term matrix for 'processed_document'
dtm_document = tfidf_vectorizer_document.transform(new_df['processed_document'])

# the top_n_papers_refined function call
top_papers = top_n_papers_refined(query="model",
    lda_model=lda_document_model,
    dtm=dtm_document,
    dataframe=new_df,
    vectorizer=tfidf_vectorizer_document,
    citation_col='citation_count',
    normalized_col='normalized_score',
    preprocess_function=preprocess_text,
    n=25,
    similarity_weight=0.6,
    citation_weight=0.3,
    normalized_weight=0.1
)

"""## Retrieved top papers after first level"""

top_papers

"""storing the df in a new variable to go through second phase of retrieval"""

df_second_level=top_papers



"""# Second level Retrieval"""

# Load the SciBERT model and tokenizer
scibert_model = AutoModel.from_pretrained('allenai/scibert_scivocab_uncased')
tokenizer = AutoTokenizer.from_pretrained('allenai/scibert_scivocab_uncased')

import pickle

def save_cache_to_file(cache, filename):
    with open(filename, 'wb') as file:
        pickle.dump(cache, file)

def load_cache_from_file(filename):
    try:
        with open(filename, 'rb') as file:
            return pickle.load(file)
    except FileNotFoundError:
        return {}  # Return an empty dictionary if the file doesn't exist

#embeddings_cache = load_cache_from_file('embeddings_cache.pkl')

"""```
#Usage of cache file
# At the beginning of your script
embeddings_cache = load_cache_from_file('embeddings_cache.pkl')

# Your existing code for processing and using the embeddings_cache
# ...

# At the end of your script
save_cache_to_file(embeddings_cache, 'embeddings_cache.pkl')


```

Sliding Window
"""

def sliding_window(text, window_size=512, stride=256):
    """
    Split the text into overlapping segments.

    :param text: The text to be split.
    :param window_size: The number of tokens in each segment.
    :param stride: The number of tokens to overlap.
    :return: A list of text segments.
    """
    # Tokenize the text
    tokens = tokenizer.tokenize(text)

    # Split tokens into overlapping segments
    segments = []
    for i in range(0, len(tokens), stride):
        segment = tokens[i:i + window_size]
        segments.append(tokenizer.convert_tokens_to_string(segment))

    return segments

"""function to get scibert embeddings"""

def get_scibert_embeddings(texts, model, tokenizer, batch_size=16):
    global embeddings_cache
    embeddings = []

    for text in texts:
        if text in embeddings_cache:
            embeddings.append(embeddings_cache[text])
        else:
            inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512).to(model.device)
            with torch.no_grad():
                output = model(**inputs)
            embedding = output.last_hidden_state.mean(dim=1).cpu().numpy()
            embeddings_cache[text] = embedding
            embeddings.append(embedding)

    # Concatenate embeddings into a 2D array
    embeddings = np.concatenate(embeddings, axis=0)
    return embeddings

"""function to retrieve the top 5 papers after implementing SciBERT model(second level retrieval)"""

def process_papers_with_scibert_top_5(dataframe, text_column, query, model, tokenizer):

    query_embedding = get_scibert_embeddings([query], model, tokenizer)[0]

    similarity_scores = []

    for index, row in dataframe.iterrows():
        windows = sliding_window(row[text_column])
        window_embeddings = get_scibert_embeddings(windows, model, tokenizer)

        max_similarity = 0
        most_similar_segment = ""
        for i, window_embedding in enumerate(window_embeddings):
            similarity = cosine_similarity([query_embedding], [window_embedding])[0][0]

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_segment = windows[i]

        similarity_scores.append((index, max_similarity, most_similar_segment))

    # Sort the papers by similarity score and select top 5
    top_5_papers = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[:5]

    # Create a DataFrame for top 5 papers using pandas.concat
    frames = [dataframe.loc[[idx]].assign(most_similar_segment=segment, similarity_score=score)
              for idx, score, segment in top_5_papers]
    top_5_df = pd.concat(frames)

    return top_5_df

"""Function to retrieve similar snippets from the text"""

def display_similar_segments(dataframe, paper_name_col):
    """
    Display the paper name, a snippet from the most similar part of the paper, and the similarity score.

    :param dataframe: The DataFrame containing the papers and their most similar segments.
    :param paper_name_col: The name of the column containing the paper names.
    """
    for index, row in dataframe.iterrows():
        print(f"Paper: {row[paper_name_col]}")
        print(f"Similarity Score: {row['similarity_score']:.4f}")

        # Extract a snippet from the most similar segment (20-30 words)
        snippet = ' '.join(row['most_similar_segment'].split()[:30])
        print(f"Snippet: {snippet}\n")


#Usage:display_similar_segments(processed_df, 'paper_name')

embeddings_cache = load_cache_from_file('embeddings_cache_v3.pkl')

# Assuming user_query, scibert_model, tokenizer, and df_second_level are already defined
#
processed_df = process_papers_with_scibert_top_5(df_second_level, 'processed_document', "model", scibert_model, tokenizer)

save_cache_to_file(embeddings_cache, 'embeddings_cache_v3.pkl')

display_similar_segments(processed_df, 'paper_name')

"""# Combined function to retrieve documents using the two-level retrieval system which takes dynamic input"""

def two_level_retrieval_system(df, preprocess_text, level1_func, level2_func, *args, **kwargs):
    query = input("Enter your query: ")
    processed_query = preprocess_text(query)

    # Apply LDA and TF-IDF
    lda_document_model, tfidf_vectorizer_document = apply_tfidf_and_lda(df, 'processed_document')

    # Level 1 Retrieval
    level1_results = level1_func(
        query=processed_query,
        lda_model=lda_document_model,
        dtm=tfidf_vectorizer_document.transform(df['processed_document']),
        dataframe=df,
        vectorizer=tfidf_vectorizer_document,
        citation_col='citation_count',
        normalized_col='normalized_score',
        preprocess_function=preprocess_text,
        *args,
        **kwargs
    )

    # Level 2 Retrieval
    final_results = level2_func(level1_results, 'processed_document', processed_query, scibert_model, tokenizer)

    return final_results

# Make sure new_df and other required components are initialized
embeddings_cache = load_cache_from_file('embeddings_cache_v3.pkl')
final_results = two_level_retrieval_system(new_df, preprocess_text, top_n_papers_refined, process_papers_with_scibert_top_5)
save_cache_to_file(embeddings_cache, 'embeddings_cache_v3.pkl')

final_results

display_similar_segments(final_results,'paper_name')



"""def retrieve_documents_for_all_ngrams(df, one_grams_col, two_grams_col, three_grams_col, preprocess_text, top_n_papers_refined, process_papers_with_scibert_top_5):
    retrieved_indices = {'1gram': [], '2gram': [], '3gram': []}

    for ngram_type, col in [('1gram', one_grams_col), ('2gram', two_grams_col), ('3gram', three_grams_col)]:
        for phrases in df[col]:
            # Convert the key phrases to a query string
            query = ' '.join(phrases) if isinstance(phrases, list) else phrases
            processed_query = preprocess_text(query)

            # Call your two-level retrieval system with the processed query
            retrieved_docs = two_level_retrieval_system(
                new_df,
                lambda x: processed_query,
                top_n_papers_refined,
                process_papers_with_scibert_top_5
            )
            # Assuming retrieved_docs is a list of indices or identifiers of the retrieved documents
            retrieved_indices[ngram_type].append(retrieved_docs)

    return retrieved_indices

def two_level_retrieval_system_for_eval(query,df, preprocess_text, level1_func, level2_func, *args, **kwargs):

    processed_query = preprocess_text(query)

    # Apply LDA and TF-IDF
    lda_summary_model, tfidf_vectorizer_summary, lda_document_model, tfidf_vectorizer_document = apply_tfidf_and_lda(df, 'processed_summary', 'processed_document')

    # Level 1 Retrieval
    level1_results = level1_func(
        query=processed_query,
        lda_model=lda_document_model,
        dtm=tfidf_vectorizer_document.transform(df['processed_document']),
        dataframe=df,
        vectorizer=tfidf_vectorizer_document,
        citation_col='citation_count',
        normalized_col='normalized_score',
        preprocess_function=preprocess_text,
        *args,
        **kwargs
    )

    # Level 2 Retrieval
    final_results = level2_func(level1_results, 'processed_document', processed_query, scibert_model, tokenizer)

    return final_results

def extract_and_separate_key_phrases(df, summary_column, n_phrases=3):
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words='english')

    X = vectorizer.fit_transform(df[summary_column])
    feature_array = np.array(vectorizer.get_feature_names_out())

    one_grams, two_grams, three_grams = [], [], []

    for i in range(X.shape[0]):
        tfidf_sorting = np.argsort(X[i].toarray()).flatten()[::-1]
        top_n = feature_array[tfidf_sorting][:n_phrases]

        one_gram = [phrase for phrase in top_n if len(phrase.split()) == 1]
        two_gram = [phrase for phrase in top_n if len(phrase.split()) == 2]
        three_gram = [phrase for phrase in top_n if len(phrase.split()) == 3]

        one_grams.append(one_gram)
        two_grams.append(two_gram)
        three_grams.append(three_gram)

    df['one_grams'] = one_grams
    df['two_grams'] = two_grams
    df['three_grams'] = three_grams

    return df

# User query simulation
"""

def extract_and_separate_key_phrases(df, summary_column, n_phrases=3):
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words='english')

    X = vectorizer.fit_transform(df[summary_column])
    feature_array = np.array(vectorizer.get_feature_names_out())

    one_grams, two_grams, three_grams = [], [], []

    for i in range(X.shape[0]):
        tfidf_sorting = np.argsort(X[i].toarray()).flatten()[::-1]
        top_n = feature_array[tfidf_sorting][:n_phrases]

        one_gram = [phrase for phrase in top_n if len(phrase.split()) == 1]
        two_gram = [phrase for phrase in top_n if len(phrase.split()) == 2]
        three_gram = [phrase for phrase in top_n if len(phrase.split()) == 3]

        one_grams.append(one_gram)
        two_grams.append(two_gram)
        three_grams.append(three_gram)

    df['one_grams'] = one_grams
    df['two_grams'] = two_grams
    df['three_grams'] = three_grams

    return df

modified_df = extract_and_separate_key_phrases(new_df, 'processed_summary', n_phrases=6)

"""Dataframe with queries"""

modified_df

print(modified_df['one_grams'].head())

"""Retrieval function that iterates over the queries and retrieved document

# Extracting the queries
"""

one_gram_queries = modified_df['one_grams'].explode().dropna().unique().tolist()
two_gram_queries = modified_df['two_grams'].explode().dropna().unique().tolist()
three_gram_queries = modified_df['three_grams'].explode().dropna().unique().tolist()

len(one_gram_queries)

len(two_gram_queries)

len(three_gram_queries)

"""#Retrieving the documents using our retrieval system (n-gram queries as input)


"""

import pandas as pd

def two_level_retrieval_system_for_ngrams(ngram_queries, df, preprocess_text, level1_func, level2_func, *args, **kwargs):
    """
    A function to perform a two-level retrieval system for n-gram queries, including dynamic generation of LDA models and TF-IDF vectorizers.

    :param ngram_queries: Dictionary of lists of n-gram queries.
    :param df: DataFrame containing the documents.
    :param preprocess_text: Function for preprocessing the queries.
    :param level1_func: Function for the first level of retrieval.
    :param level2_func: Function for the second level of retrieval.
    :param args: Additional arguments.
    :param kwargs: Keyword arguments.
    :return: DataFrame with results for each n-gram type.
    """
    # Create an 'index' column in the original DataFrame
    df['index'] = df.index

    # Initialize a list to collect results
    results = []

    # Other initializations as before
    lda_document_model, tfidf_vectorizer_document = apply_tfidf_and_lda(df,'processed_document')

    for ngram_type, queries in ngram_queries.items():
        for query in queries:
            processed_query = preprocess_text(query)

            # Level 1 Retrieval as before
            level1_results = level1_func(
                query=processed_query,
                lda_model=lda_document_model,
                dtm=tfidf_vectorizer_document.transform(df['processed_document']),
                dataframe=df,
                vectorizer=tfidf_vectorizer_document,
                citation_col='citation_count',
                normalized_col='normalized_score',
                preprocess_function=preprocess_text,
                n=25,
                similarity_weight=0.7,
                citation_weight=0.2,
                normalized_weight=0.1,
                *args, **kwargs
            )

            # Level 2 Retrieval as before
            final_results = level2_func(level1_results, 'processed_document', processed_query, scibert_model, tokenizer)

            # Collect the results
            for index in final_results.index:
                document_row = df.loc[index]  # Get the corresponding document row from the original DataFrame
                result_row = {
                    'ngram_type': ngram_type,
                    'query': query,
                    'index': index,
                    'processed_document': document_row.get('processed_document', None),  # Handle missing column
                    'processed_summary': document_row.get('processed_summary', None),  # Handle missing column
                    'normalized_score': document_row.get('normalized_score', None),  # Handle missing column
                    'citation_count': document_row.get('citation_count', None),  # Handle missing column
                    'paper_name': document_row.get('paper_name', None),  # Handle missing column
                    'combined_score': document_row.get('combined_score', None),  # Handle missing column
                    'most_similar_segment': document_row.get('most_similar_segment', None),  # Handle missing column
                    'similarity_score': document_row.get('similarity_score', None),  # Handle missing column
                }

                results.append(result_row)

    # Create a DataFrame from the collected results
    result_df = pd.DataFrame(results)

    return result_df

embeddings_cache = load_cache_from_file('embeddings_cache_v3.pkl')

# using 100 random 1 grams and 2 grams queries to evaluate
random_one_gram_queries = random.sample(one_gram_queries, 100)
random_two_gram_queries = random.sample(two_gram_queries, 100)

ngram_queries = {
    '1gram': random_one_gram_queries,
    '2gram': random_two_gram_queries,
}

retrieval_results = two_level_retrieval_system_for_ngrams(
    ngram_queries,
    df=new_df,
    preprocess_text=preprocess_text,
    level1_func=top_n_papers_refined,
    level2_func=process_papers_with_scibert_top_5
    # Additional arguments
)
save_cache_to_file(embeddings_cache, 'embeddings_cache_v3.pkl')

"""
for using all ngram queries
```
ngram_queries = {
    '1gram': one_gram_queries,
    '2gram': two_gram_queries,
    '3gram': three_gram_queries,

}

retrieval_results = two_level_retrieval_system_for_ngrams(
    ngram_queries,
    df=new_df,
    preprocess_text=preprocess_text,
    level1_func=top_n_papers_refined,
    level2_func=process_papers_with_scibert_top_5
    # Additional arguments
)
save_cache_to_file(embeddings_cache, 'embeddings_cache_v3.pkl')
```

"""

retrieval_results.head()

# creating a new dataframe with only needed columns for evaluation
retrieved_docs_df = retrieval_results[['ngram_type', 'index', 'query']].copy()

"""# Retrieving relevant docs from the summaries using sciBERT embeddings(n-gram queries as input)"""

def find_relevant_docs_based_on_summary(query, all_documents, model, tokenizer, top_n=35):
    """
    Find relevant documents for a given query based on similarity to document summaries.

    :param query: The query string.
    :param all_documents: List of all document summaries.
    :param model: SciBERT model for embedding generation.
    :param tokenizer: Tokenizer for the SciBERT model.
    :param top_n: Number of top relevant documents to return.
    :return: Indices of the top_n relevant documents.
    """
    query_embedding = get_scibert_embeddings(query, model, tokenizer)[0]
    doc_embeddings = [get_scibert_embeddings(doc_summary, model, tokenizer)[0] for doc_summary in all_documents]

    # Calculating cosine similarity
    similarities = cosine_similarity([query_embedding], doc_embeddings)[0]

    # Getting indices of documents in descending order of similarity
    sorted_doc_indices = np.argsort(similarities)[::-1]

    # Selecting the top_n indices
    relevant_doc_indices = sorted_doc_indices[:top_n]
    return relevant_doc_indices.tolist()

def find_relevant_docs_for_all_ngrams(ngram_queries, all_summaries, all_documents, model, tokenizer, top_n=35):
    """
    Find relevant documents for all n-gram queries and return a comprehensive DataFrame.

    :param ngram_queries: Dictionary with n-gram queries.
    :param all_summaries: List of all document summaries.
    :param all_documents: DataFrame containing all documents with their details.
    :param model: SciBERT model for embedding generation.
    :param tokenizer: Tokenizer for the SciBERT model.
    :param top_n: Number of top relevant documents to return for each query.
    :return: DataFrame with detailed information of relevant documents for all n-gram queries.
    """
    all_relevant_docs = pd.DataFrame()

    for ngram_type, queries in ngram_queries.items():
        for query in queries:
            relevant_docs_indices = find_relevant_docs_based_on_summary(
                query, all_summaries, model, tokenizer, top_n)
            relevant_docs_df = all_documents.iloc[relevant_docs_indices].copy()
            relevant_docs_df['ngram_type'] = ngram_type
            relevant_docs_df['query'] = query
            all_relevant_docs = pd.concat([all_relevant_docs, relevant_docs_df])

    return all_relevant_docs

all_summaries = new_df['processed_summary'].tolist()  # List of document summaries
all_documents = new_df # DataFrame containing all documents

comprehensive_relevant_docs_df = find_relevant_docs_for_all_ngrams(
    ngram_queries,
    all_summaries,
    all_documents,
    scibert_model,
    tokenizer
)

# Extracting the required columns
relevant_docs_df = comprehensive_relevant_docs_df[['ngram_type', 'query','index']]

"""Retrieved docs and Relevant docs"""

retrieved_docs_df

relevant_docs_df

"""# Evaluation

"""

def evaluate_by_ngram_category(retrieved_df, ground_truth_df):
    categories = ['1gram', '2gram', '3gram']
    evaluation_results = {}

    for category in categories:
        # Filter dataframes by ngram category
        retrieved_category_df = retrieved_df[retrieved_df['ngram_type'] == category]
        ground_truth_category_df = ground_truth_df[ground_truth_df['ngram_type'] == category]

        # Get unique queries in the category
        queries = set(retrieved_category_df['query'].unique()).union(set(ground_truth_category_df['query'].unique()))

        # Initialize metrics
        precision_scores, recall_scores, f1_scores = [], [], []

        for query in queries:
            # Get the indices of retrieved and relevant documents for the query
            retrieved_indices = set(retrieved_category_df[retrieved_category_df['query'] == query]['index'])
            relevant_indices = set(ground_truth_category_df[ground_truth_category_df['query'] == query]['index'])

            # Calculate precision, recall, and F1 score
            true_positives = len(retrieved_indices.intersection(relevant_indices))
            precision = true_positives / len(retrieved_indices) if retrieved_indices else 0
            recall = true_positives / len(relevant_indices) if relevant_indices else 0
            f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

            precision_scores.append(precision)
            recall_scores.append(recall)
            f1_scores.append(f1_score)

        # Average the scores
        avg_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0
        avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0
        avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0

        evaluation_results[category] = {
            'Precision@k': avg_precision,
            'Recall@k': avg_recall,
            'F1 Score@k': avg_f1
        }

    return evaluation_results

# Example usage
evaluation_results = evaluate_by_ngram_category(retrieved_docs_df, relevant_docs_df)

evaluation_results



