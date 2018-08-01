"""
test program for mean, a TransformerPrimitive imputer
"""
import sys

def text2int(col):
    """
    convert column value from text to integer codes (0,1,2...)
    """
    return pd.DataFrame(col.astype('category').cat.codes, columns=[col.name])


import pandas as pd
import os

from d3m.container.dataset import D3MDatasetLoader, Dataset, CSVLoader

from dsbox.datapreprocessing.cleaner import MeanImputation, MeanHyperparameter

from dsbox.datapreprocessing.cleaner.denormalize import Denormalize, DenormalizeHyperparams as hyper_DE
from common_primitives.dataset_to_dataframe import DatasetToDataFramePrimitive, Hyperparams as hyper_DD
from common_primitives.extract_columns_semantic_types import ExtractColumnsBySemanticTypesPrimitive

h_DE = hyper_DE.defaults()
h_DD =hyper_DD.defaults()

h_attr = {'semantic_types': ('https://metadata.datadrivendiscovery.org/types/Attribute',),'use_columns': (), 'exclude_columns': ()}
h_target = {'semantic_types': ('https://metadata.datadrivendiscovery.org/types/Target','https://metadata.datadrivendiscovery.org/types/SuggestedTarget',), 'use_columns': (), 'exclude_columns': ()}

primitive_0 = Denormalize(hyperparams=h_DE)
primitive_1 = DatasetToDataFramePrimitive(hyperparams=h_DD)

primitive_3 = ExtractColumnsBySemanticTypesPrimitive(hyperparams=h_attr)

# global variables
dataset_file_path = "dsbox/unit_tests/resources/38_sick_data/datasetDoc.json"

dataset = D3MDatasetLoader()
dataset = dataset.load('file://{dataset_doc_path}'.format(dataset_doc_path=os.path.abspath(dataset_file_path)))

result0 = primitive_0.produce(inputs=dataset)
result1 = primitive_1.produce(inputs=result0.value)

X = primitive_3.produce(inputs=result1.value).value


# label = text2int(pd.read_csv(label_name, index_col='d3mIndex')["Class"])
hp = MeanHyperparameter.sample()

import unittest


class TestMean(unittest.TestCase):

    def setUp(self):
        self.enough_time = 100
        self.not_enough_time = 0.000001

    def test_init(self):

        imputer = MeanImputation(hyperparams=hp)
        self.assertEqual(imputer._has_finished, False)
        self.assertEqual(imputer._iterations_done, False)

    def test_run(self):
        # part 1
        imputer = MeanImputation(hyperparams=hp)

        imputer.set_training_data(inputs=X)
        imputer.fit(timeout=self.enough_time)
        # print(imputer.get_params())
        self.assertEqual(imputer._has_finished, True)
        self.assertEqual(imputer._iterations_done, True)

        result = imputer.produce(inputs=X, timeout=self.enough_time).value
        self.helper_impute_result_check(X, result)

        # part2: test set_params()
        imputer2 = MeanImputation(hyperparams=hp)

        imputer2.set_params(params=imputer.get_params())
        self.assertEqual(imputer2._has_finished, True)
        self.assertEqual(imputer2._iterations_done, True)

        result2 = imputer2.produce(inputs=X, timeout=self.enough_time).value
        self.assertEqual(result2.equals(result), True)  # two imputers' results should be same
        self.assertEqual(imputer2._has_finished, True)
        self.assertEqual(imputer2._iterations_done, True)

    # mean imputation is too fast to make it timeout

    # def test_timeout(self):
    # 	imputer = MeanImputation(hyperparams=hp)
    # 	imputer.set_training_data(inputs=X)
    # 	imputer.fit(timeout=self.not_enough_time)
    # 	self.assertEqual(imputer.get_call_metadata(),
    # 		CallMetadata(has_finished=False, iterations_done=False))
    # 	with self.assertRaises(ValueError):	# ValueError is because: have on fitted yet
    # 		result = imputer.produce(inputs=X, timeout=self.not_enough_time)

    def test_noMV(self):
        """
        test on the dataset has no missing values
        """
        imputer = MeanImputation(hyperparams=hp)

        imputer.set_training_data(inputs=X)
        imputer.fit(timeout=self.enough_time)
        result = imputer.produce(inputs=X, timeout=self.enough_time).value
        # 1. check produce(): `result` contains no missing value
        result2 = imputer.produce(inputs=result, timeout=self.enough_time).value

        self.assertEqual(result.equals(result2), True)

        # 2. check fit() & get_params() try fit on no-missing-value dataset
        imputer2 = MeanImputation(hyperparams=hp)
        imputer2.set_training_data(inputs=result)
        imputer2.fit(timeout=self.enough_time)
        # print(imputer.get_params())

    def test_notAlign(self):
        """
        test the case that the missing value situations in trainset and testset are not aligned. eg:
            `a` missing-value columns in trainset, `b` missing-value columns in testset.
            `a` > `b`, or `a` < `b`
        """

        imputer = MeanImputation(hyperparams=hp)
        imputer.set_training_data(inputs=X)
        imputer.fit(timeout=self.enough_time)
        result = imputer.produce(inputs=X, timeout=self.enough_time).value
        # PART1: when `a` > `b`
        data2 = result.copy()
        data2["T3"] = X["T3"].copy()  # only set this column to original column, with missing vlaues
        result2 = imputer.produce(inputs=data2, timeout=self.enough_time).value
        self.helper_impute_result_check(data2, result2)

        # PART2: when `a` < `b`

        imputer = MeanImputation(hyperparams=hp)
        imputer.set_training_data(inputs=data2)
        imputer.fit(timeout=self.enough_time)
        result = imputer.produce(inputs=X, timeout=self.enough_time).value
        # data contains more missingvalue columns than data2,
        # the imputer should triger default impute method for the column that not is trained
        self.helper_impute_result_check(X, result)

        # PART3: trunk the data : sample wise

        imputer = MeanImputation(hyperparams=hp)
        imputer.set_training_data(inputs=X)
        imputer.fit(timeout=self.enough_time)
        result = imputer.produce(inputs=X[0:20], timeout=self.enough_time).value
        self.helper_impute_result_check(X[0:20], result)

    def helper_impute_result_check(self, data, result):
        """
        check if the imputed reuslt valid
        now, check for:
        1. contains no nan anymore
        2. orignal non-nan value should remain the same
        """
        # check 1
        nan_sum = 0
        for col_name in result:
            for i in result[col_name].index:
                if result[col_name][i] == "" or pd.isnull(data[col_name][i]):
                    nan_sum += 1

        self.assertEqual(nan_sum, 0)

        # check 2
        # the original non-missing values must keep unchanged
        # to check, cannot use pd equals, since the imputer may convert:
        # 1 -> 1.0
        # have to do loop checking
        # after DatasetToDataframe, every dtype became object
        for col_name in data:
            for i in data[col_name].index:
                if data[col_name][i]:
                    if isinstance(data[col_name][i], int) or isinstance(data[col_name][i], float) or data[col_name][i].isnumeric():
                        self.assertEqual(float(data[col_name][i]) == float(result[col_name][i]), True,
                                         msg="not equals in column: {}".format(col_name))
                    else:
                        self.assertEqual(str(data[col_name][i]) == str(result[col_name][i]), True,
                                         msg="not equals in column: {}".format(col_name))


if __name__ == '__main__':
    unittest.main()
