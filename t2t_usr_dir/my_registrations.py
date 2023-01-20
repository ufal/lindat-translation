from tensor2tensor.utils import registry
from tensor2tensor.data_generators import translate, problem, text_encoder, generator_utils
from tensor2tensor.data_generators.translate_encs import TranslateEncsWmt32k

_ENCS_TRAIN_DATASETS = [
    [("http://czeng57m.tar"),
     ("tsv", 3, 2, "czeng57m/*train.gz")],
    [
        "http://data.statmt.org/wmt17/translation-task/training-parallel-nc-v12.tgz",  # pylint: disable=line-too-long
        ("training/news-commentary-v12.cs-en.en",
         "training/news-commentary-v12.cs-en.cs")
    ],
    [
        "http://www.statmt.org/wmt13/training-parallel-commoncrawl.tgz",
        ("commoncrawl.cs-en.en", "commoncrawl.cs-en.cs")
    ],
    [
        "http://www.statmt.org/wmt13/training-parallel-europarl-v7.tgz",
        ("training/europarl-v7.cs-en.en", "training/europarl-v7.cs-en.cs")
    ],
]
_ENCS_TEST_DATASETS = [
    [
        "http://data.statmt.org/wmt17/translation-task/dev.tgz",
        ("dev/newstest2013.en", "dev/newstest2013.cs")
    ],
]


@registry.register_problem
class TranslateEncsWmtCzeng57m32k(translate.TranslateProblem):
  """Problem spec for WMT English-Czech translation."""

  @property
  def targeted_vocab_size(self):
    return 2**15  # 32768

  @property
  def vocab_name(self):
    return "vocab.encs"

  def generator(self, data_dir, tmp_dir, train):
    datasets = _ENCS_TRAIN_DATASETS if train else _ENCS_TEST_DATASETS
    tag = "train" if train else "dev"
    vocab_datasets = []
    data_path = translate.compile_data(tmp_dir, datasets,
                                       "czeng57m_encs_tok_%s" % tag)
    # CzEng contains 100 gz files with tab-separated columns, so let's expect
    # it is the first dataset in datasets and use the newly created *.lang{1,2}
    # files for vocab construction.
    if datasets[0][0].endswith("czeng57m.tar"):
      vocab_datasets.append([
          datasets[0][0],
          ["czeng57m_encs_tok_%s.lang1" % tag,
           "czeng57m_encs_tok_%s.lang2" % tag]
      ])
      datasets = datasets[1:]
    vocab_datasets += [[item[0], [item[1][0], item[1][1]]] for item in datasets]
    symbolizer_vocab = generator_utils.get_or_generate_vocab(
        data_dir, tmp_dir, self.vocab_file, self.targeted_vocab_size,
        vocab_datasets)
    return translate.token_generator(data_path + ".lang1", data_path + ".lang2",
                                     symbolizer_vocab, text_encoder.EOS_ID)

  @property
  def input_space_id(self):
    return problem.SpaceID.EN_TOK

  @property
  def target_space_id(self):
    return problem.SpaceID.CS_TOK


@registry.register_problem
class TranslateMedical8lang(TranslateEncsWmt32k):
    @property
    def vocab_filename(self):
        return "vocab_medical8lang.%d" % self.approx_vocab_size


@registry.register_problem
class TranslateEnde(TranslateEncsWmtCzeng57m32k):
    @property
    def vocab_filename(self):
        return "vocab.ende.%d" % self.approx_vocab_size


@registry.register_problem
class TranslateEnru(TranslateEncsWmtCzeng57m32k):
    @property
    def vocab_filename(self):
        return "vocab.enru.%d" % self.approx_vocab_size


@registry.register_problem
class TranslateEnpl(TranslateEncsWmtCzeng57m32k):
    @property
    def vocab_filename(self):
        return "vocab.enpl.%d" % self.approx_vocab_size

@registry.register_problem
class TranslateCsuk(TranslateEncsWmtCzeng57m32k):
    @property
    def vocab_filename(self):
        return "vocab.csuk.%d" % self.approx_vocab_size

@registry.register_problem
class TranslateCsuk4(TranslateEncsWmtCzeng57m32k):
    @property
    def vocab_filename(self):
        return "vocab.csuk4.%d" % self.approx_vocab_size

@registry.register_problem
class TranslateCsru(TranslateEncsWmtCzeng57m32k):
    @property
    def vocab_filename(self):
        return "vocab.csru.%d" % self.approx_vocab_size

