import torch
from torch import nn
from torch.nn.init import xavier_normal_, xavier_uniform_

from tucker_riemopt import Tucker


class R_TuckER(nn.Module):
    def __init__(self, data_count, rank=None, **kwargs):
        """
        Parameters:
        -----------
        data_count: tuple
            (entities_count, relations_count) --- number of objects of corresponding kind in dataset
        rank: Sequence[int]
            rank of the manifold
        """
        super().__init__()

        self.S = nn.Embedding(data_count[0], rank[1])
        self.R = nn.Embedding(data_count[1], rank[0])
        self.O = nn.Embedding(data_count[0], rank[2])
        self.core = nn.Parameter(torch.zeros(tuple(rank), dtype=torch.float32))

        self.rank = rank
        self.device = "cpu"

        self.bn0 = nn.BatchNorm1d(rank[1])
        self.bn1 = nn.BatchNorm1d(rank[0])

    def init(self, state_dict=None):
        if state_dict:
            self.load_state_dict(state_dict)
        else:
            xavier_uniform_(self.core)
            xavier_normal_(self.S.weight)
            xavier_normal_(self.R.weight)
            xavier_normal_(self.O.weight)

    def forward(self, subject_idx, relation_idx):
        relations = self.R(relation_idx)
        subjects = self.S(subject_idx)

        def forward_core(T: Tucker):
            relations = T.factors[0][relation_idx, :]
            subjects = T.factors[1][subject_idx, :]
            preds = torch.einsum("abc,da->dbc", T.core, relations)
            preds = torch.bmm(subjects.view(-1, 1, subjects.shape[1]), preds).view(-1, subjects.shape[1])
            preds = preds @ T.factors[2].T
            return torch.sigmoid(preds)

        preds = torch.einsum("abc,da->dbc", self.core, relations)
        preds = torch.bmm(subjects.view(-1, 1, subjects.shape[1]), preds).view(-1, subjects.shape[1])
        preds = preds @ self.O.weight.T
        return torch.sigmoid(preds), forward_core
