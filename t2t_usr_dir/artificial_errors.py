from tensor2tensor.data_generators import problem
from tensor2tensor.data_generators import text_problems
from tensor2tensor.utils import registry

@registry.register_problem
class ArtificialErrors(text_problems.Text2TextProblem):

    @property
    def approx_vocab_size(self):
        return 2 ** 15 # ~32k

    @property
    def vocab_filename(self):
        return "vocab.artificial_errors"


@registry.register_problem
class ArtificialErrorsCs(ArtificialErrors):
    @property
    def vocab_filename(self):
        return "vocab.cs.artificial_errors.%d" % self.approx_vocab_size


@registry.register_problem
class ArtificialErrorsDe(ArtificialErrors):
    @property
    def vocab_filename(self):
        return "vocab.de.artificial_errors.%d" % self.approx_vocab_size


@registry.register_problem
class ArtificialErrorsEn(ArtificialErrors):
    @property
    def vocab_filename(self):
        return "vocab.en.artificial_errors.%d" % self.approx_vocab_size


@registry.register_problem
class ArtificialErrorsRu(ArtificialErrors):
    @property
    def vocab_filename(self):
        return "vocab.ru.artificial_errors.%d" % self.approx_vocab_size

