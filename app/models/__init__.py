from .model import Model, hparams, log, T2T_AVAILABLE
from .marian_model import MarianModel
from .oai_llm_model import OaiLLMModel

# Only import T2T models if tensor2tensor is available
if T2T_AVAILABLE:
    from .t2t_model import T2TModel, T2TDocModel, T2TModelWithScores
else:
    # Define placeholder classes if T2T is not available
    T2TModel = None
    T2TDocModel = None
    T2TModelWithScores = None