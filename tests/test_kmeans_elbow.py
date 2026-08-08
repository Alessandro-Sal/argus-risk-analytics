import numpy as np
from sklearn.cluster import KMeans

def test_kmeans_inertia_monotonic_decrease():
    # Mock dataset of 10 points in risk-return space (2D)
    np.random.seed(42)
    data = np.random.rand(10, 2)
    
    inertias = []
    k_values = list(range(1, 6)) # K = 1, 2, 3, 4, 5
    
    for k in k_values:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(data)
        inertias.append(km.inertia_)
        
    # Check that inertia decreases as K increases: inertia[k] <= inertia[k-1]
    for i in range(1, len(inertias)):
        assert inertias[i] <= inertias[i-1] + 1e-7
