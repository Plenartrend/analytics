import networkx as nx
from matplotlib import pyplot as plt
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


def build_speech_graph(speeches, min_similarity=0.35):
    G = nx.Graph()

    for idx, sp in enumerate(speeches):
        G.add_node(idx, topics=sp.topics, text_preview=sp.text[:250])

    speeches_text = [f"{'; '.join(sp.topics)} | {sp.text}" for sp in speeches]

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = model.encode(speeches_text)

    similarity_matrix = cosine_similarity(embeddings)

    num_speeches = len(speeches)
    for i in range(num_speeches):
        for j in range(i + 1, num_speeches):
            sim = similarity_matrix[i, j]

            if sim >= min_similarity:
                G.add_edge(i, j, weight=float(sim))

    return G


def generate_speech_graph(topic_classified_speeches, min_similarity=0.35):
    G = build_speech_graph(topic_classified_speeches, min_similarity)
    plt.figure(figsize=(12, 10))
    pos = nx.spring_layout(G, k=0.8, seed=42)
    nx.draw_networkx_nodes(G, pos, node_color="lightblue", node_size=1200)
    labels = {
        n: f"Id: {topic_classified_speeches[n].id}\n" + "\n".join(topic_classified_speeches[n].topics[:2])
        for n in G.nodes()
    }
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7)
    edges = G.edges(data=True)
    nx.draw_networkx_edges(
        G,
        pos,
        edgelist=[(u, v) for u, v, _ in edges],
        width=[d["weight"] * 4 for _, _, d in edges],
    )
    plt.title("Speech-to-Speech Similarity Graph")
    plt.axis("off")
    plt.show()
