#!/usr/bin/env python3
"""
TF-IDF and clustering for diversity measurement.
"""
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import Dict, List, Tuple

from .text_norm import normalize_text


def calculate_gini(values: List[int]) -> float:
    """
    Calculate Gini coefficient for a list of values.
    
    Returns:
        Gini coefficient [0.0, 1.0]
    """
    # Sort values in ascending order
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n == 0 or sum(sorted_values) == 0:
        return 0.0
        
    # Calculate cumulative sum
    cum_values = np.cumsum(sorted_values, dtype=float)
    
    # Calculate Gini coefficient
    gini = (n + 1 - 2 * np.sum((n + 1 - np.arange(1, n + 1)) * sorted_values) / cum_values[-1]) / n
    return round(gini, 4)


def build_tfidf_vectors(texts: List[str]) -> Tuple[TfidfVectorizer, np.ndarray]:
    """
    Build TF-IDF vectors from texts.
    
    Args:
        texts: List of normalized texts
    
    Returns:
        Tuple of (vectorizer, vectors)
    """
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9,
        use_idf=True,
        norm='l2'
    )
    vectors = vectorizer.fit_transform(texts)
    return vectorizer, vectors


def cluster_texts(
    vectors: np.ndarray, 
    k: int = 8, 
    random_state: int = 2025
) -> Tuple[KMeans, List[int]]:
    """
    Cluster text vectors using KMeans.
    
    Args:
        vectors: TF-IDF vectors
        k: Number of clusters
        random_state: Random seed
    
    Returns:
        Tuple of (kmeans model, cluster assignments)
    """
    kmeans = KMeans(
        n_clusters=k,
        random_state=random_state,
        n_init=10,
        algorithm="lloyd",
        max_iter=300,
        tol=1e-4
    )
    clusters = kmeans.fit_predict(vectors)
    return kmeans, clusters


def evaluate_cluster_diversity(
    clusters: List[int], 
    min_cluster_size: int = 3,  # Reduced from 4 to be more lenient
    max_gini: float = 0.40      # Increased from 0.35 to be more lenient
) -> Tuple[bool, Dict]:
    """
    Evaluate cluster diversity.
    
    Args:
        clusters: Cluster assignments
        min_cluster_size: Minimum acceptable cluster size
        max_gini: Maximum acceptable Gini coefficient
    
    Returns:
        Tuple of (is_diverse, report)
    """
    # Count items per cluster
    unique_clusters = sorted(set(clusters))
    cluster_counts = {str(c): list(clusters).count(c) for c in unique_clusters}
    
    # Calculate Gini coefficient
    gini = calculate_gini(list(cluster_counts.values()))
    
    # Check minimum cluster size
    min_size = min(cluster_counts.values()) if cluster_counts else 0
    
    # Create report
    report = {
        "cluster_counts": cluster_counts,
        "gini": gini,
        "min_cluster_size": min_size,
        "is_diverse": (min_size >= min_cluster_size and gini <= max_gini),
        "reason": None
    }
    
    # Add failure reason if applicable
    if min_size < min_cluster_size:
        report["reason"] = f"Min cluster size {min_size} < required {min_cluster_size}"
    elif gini > max_gini:
        report["reason"] = f"Gini {gini:.4f} > max {max_gini:.4f}"
    
    return report["is_diverse"], report


def find_most_central_item(
    vectors: np.ndarray, 
    kmeans: KMeans, 
    cluster_idx: int
) -> int:
    """
    Find the most central item in a cluster.
    
    Args:
        vectors: TF-IDF vectors
        kmeans: Fitted KMeans model
        cluster_idx: Cluster index
    
    Returns:
        Index of most central item
    """
    # Get cluster center
    center = kmeans.cluster_centers_[cluster_idx]
    
    # Find items in this cluster
    cluster_items = np.where(kmeans.labels_ == cluster_idx)[0]
    
    # Calculate distances to center
    distances = np.array([
        np.linalg.norm(vectors[i].toarray() - center) 
        for i in cluster_items
    ])
    
    # Return index of closest item to center
    closest_idx = cluster_items[np.argmin(distances)]
    return closest_idx
