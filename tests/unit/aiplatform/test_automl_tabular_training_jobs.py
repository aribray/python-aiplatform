import importlib
import pytest
from unittest import mock

from google.cloud import aiplatform
from google.cloud.aiplatform import datasets
from google.cloud.aiplatform import initializer
from google.cloud.aiplatform import schema
from google.cloud.aiplatform.training_jobs import AutoMLTabularTrainingJob

from google.cloud.aiplatform_v1beta1.services.model_service import (
    client as model_service_client,
)
from google.cloud.aiplatform_v1beta1.services.pipeline_service import (
    client as pipeline_service_client,
)
from google.cloud.aiplatform_v1beta1.types import model as gca_model
from google.cloud.aiplatform_v1beta1.types import pipeline_state as gca_pipeline_state
from google.cloud.aiplatform_v1beta1.types import (
    training_pipeline as gca_training_pipeline,
)
from google.cloud.aiplatform_v1beta1 import Dataset as GapicDataset

from google.protobuf import json_format
from google.protobuf import struct_pb2

_TEST_BUCKET_NAME = "test-bucket"
_TEST_GCS_PATH_WITHOUT_BUCKET = "path/to/folder"
_TEST_GCS_PATH = f"{_TEST_BUCKET_NAME}/{_TEST_GCS_PATH_WITHOUT_BUCKET}"
_TEST_GCS_PATH_WITH_TRAILING_SLASH = f"{_TEST_GCS_PATH}/"
_TEST_PROJECT = "test-project"

_TEST_DATASET_DISPLAY_NAME = "test-dataset-display-name"
_TEST_DATASET_NAME = "test-dataset-name"
_TEST_DISPLAY_NAME = "test-display-name"
_TEST_TRAINING_CONTAINER_IMAGE = "gcr.io/test-training/container:image"
_TEST_METADATA_SCHEMA_URI_TABULAR = schema.dataset.metadata.tabular
_TEST_METADATA_SCHEMA_URI_NONTABULAR = schema.dataset.metadata.image

_TEST_TRAINING_COLUMN_TRANSFORMATIONS = [
    {"auto": {"column_name": "sepal_width"}},
    {"auto": {"column_name": "sepal_length"}},
    {"auto": {"column_name": "petal_length"}},
    {"auto": {"column_name": "petal_width"}},
]
_TEST_TRAINING_TARGET_COLUMN = "target"
_TEST_TRAINING_BUDGET_MILLI_NODE_HOURS = 1000
_TEST_TRAINING_WEIGHT_COLUMN = "weight"
_TEST_TRAINING_DISABLE_EARLY_STOPPING = True
_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME = "minimize-log-loss"
_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE = "classification"
_TEST_TRAINING_TASK_INPUTS = json_format.ParseDict(
    {
        # required inputs
        "targetColumn": _TEST_TRAINING_TARGET_COLUMN,
        "transformations": _TEST_TRAINING_COLUMN_TRANSFORMATIONS,
        "trainBudgetMilliNodeHours": _TEST_TRAINING_BUDGET_MILLI_NODE_HOURS,
        # optional inputs
        "weightColumnName": _TEST_TRAINING_WEIGHT_COLUMN,
        "disableEarlyStopping": _TEST_TRAINING_DISABLE_EARLY_STOPPING,
        "predictionType": _TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
        "optimizationObjective": _TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
        "optimizationObjectiveRecallValue": None,
        "optimizationObjectivePrecisionValue": None,
    },
    struct_pb2.Value(),
)

_TEST_DATASET_NAME = "test-dataset-name"

_TEST_MODEL_DISPLAY_NAME = "model-display-name"
_TEST_TRAINING_FRACTION_SPLIT = 0.6
_TEST_VALIDATION_FRACTION_SPLIT = 0.2
_TEST_TEST_FRACTION_SPLIT = 0.2
_TEST_PREDEFINED_SPLIT_COLUMN_NAME = "split"

_TEST_OUTPUT_PYTHON_PACKAGE_PATH = "gs://test/ouput/python/trainer.tar.gz"

_TEST_MODEL_NAME = "projects/my-project/locations/us-central1/models/12345"

_TEST_PIPELINE_RESOURCE_NAME = (
    "projects/my-project/locations/us-central1/trainingPipeline/12345"
)


class TestAutoMLTabularTrainingJob:
    def setup_method(self):
        importlib.reload(initializer)
        importlib.reload(aiplatform)

    @pytest.fixture
    def mock_pipeline_service_create(self):
        with mock.patch.object(
            pipeline_service_client.PipelineServiceClient, "create_training_pipeline"
        ) as mock_create_training_pipeline:
            mock_create_training_pipeline.return_value = gca_training_pipeline.TrainingPipeline(
                name=_TEST_PIPELINE_RESOURCE_NAME,
                state=gca_pipeline_state.PipelineState.PIPELINE_STATE_SUCCEEDED,
                model_to_upload=gca_model.Model(name=_TEST_MODEL_NAME),
            )
            yield mock_create_training_pipeline

    @pytest.fixture
    def mock_pipeline_service_create_with_no_model_to_upload(self):
        with mock.patch.object(
            pipeline_service_client.PipelineServiceClient, "create_training_pipeline"
        ) as mock_create_training_pipeline:
            mock_create_training_pipeline.return_value = gca_training_pipeline.TrainingPipeline(
                name=_TEST_PIPELINE_RESOURCE_NAME,
                state=gca_pipeline_state.PipelineState.PIPELINE_STATE_SUCCEEDED,
            )
            yield mock_create_training_pipeline

    @pytest.fixture
    def mock_pipeline_service_create_and_get_with_fail(self):
        with mock.patch.object(
            pipeline_service_client.PipelineServiceClient, "create_training_pipeline"
        ) as mock_create_training_pipeline:
            mock_create_training_pipeline.return_value = gca_training_pipeline.TrainingPipeline(
                name=_TEST_PIPELINE_RESOURCE_NAME,
                state=gca_pipeline_state.PipelineState.PIPELINE_STATE_RUNNING,
            )

            with mock.patch.object(
                pipeline_service_client.PipelineServiceClient, "get_training_pipeline"
            ) as mock_get_training_pipeline:
                mock_get_training_pipeline.return_value = gca_training_pipeline.TrainingPipeline(
                    name=_TEST_PIPELINE_RESOURCE_NAME,
                    state=gca_pipeline_state.PipelineState.PIPELINE_STATE_FAILED,
                )

                yield mock_create_training_pipeline, mock_get_training_pipeline

    @pytest.fixture
    def mock_model_service_get(self):
        with mock.patch.object(
            model_service_client.ModelServiceClient, "get_model"
        ) as mock_get_model:
            mock_get_model.return_value = gca_model.Model()
            yield mock_get_model

    @pytest.fixture
    def mock_dataset_tabular(self):
        ds = mock.MagicMock(datasets.Dataset)
        ds.name = _TEST_DATASET_NAME
        ds._gca_resource = GapicDataset(
            display_name=_TEST_DATASET_DISPLAY_NAME,
            metadata_schema_uri=_TEST_METADATA_SCHEMA_URI_TABULAR,
            labels={},
            name=_TEST_DATASET_NAME,
            metadata={},
        )
        return ds

    @pytest.fixture
    def mock_dataset_nontabular(self):
        ds = mock.MagicMock(datasets.Dataset)
        ds.name = _TEST_DATASET_NAME
        ds._gca_resource = GapicDataset(
            display_name=_TEST_DATASET_DISPLAY_NAME,
            metadata_schema_uri=_TEST_METADATA_SCHEMA_URI_NONTABULAR,
            labels={},
            name=_TEST_DATASET_NAME,
            metadata={},
        )
        return ds

    def test_run_call_pipeline_service_create(
        self,
        mock_pipeline_service_create,
        mock_dataset_tabular,
        mock_model_service_get,
    ):
        aiplatform.init(project=_TEST_PROJECT, staging_bucket=_TEST_BUCKET_NAME)

        job = AutoMLTabularTrainingJob(
            display_name=_TEST_DISPLAY_NAME,
            optimization_objective=_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
            optimization_prediction_type=_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
            column_transformations=_TEST_TRAINING_COLUMN_TRANSFORMATIONS,
            optimization_objective_recall_value=None,
            optimization_objective_precision_value=None,
        )

        model_from_job = job.run(
            dataset=mock_dataset_tabular,
            target_column=_TEST_TRAINING_TARGET_COLUMN,
            model_display_name=_TEST_MODEL_DISPLAY_NAME,
            training_fraction_split=_TEST_TRAINING_FRACTION_SPLIT,
            validation_fraction_split=_TEST_VALIDATION_FRACTION_SPLIT,
            test_fraction_split=_TEST_TEST_FRACTION_SPLIT,
            predefined_split_column_name=_TEST_PREDEFINED_SPLIT_COLUMN_NAME,
            weight_column=_TEST_TRAINING_WEIGHT_COLUMN,
            budget_milli_node_hours=_TEST_TRAINING_BUDGET_MILLI_NODE_HOURS,
            disable_early_stopping=_TEST_TRAINING_DISABLE_EARLY_STOPPING,
        )

        true_fraction_split = gca_training_pipeline.FractionSplit(
            training_fraction=_TEST_TRAINING_FRACTION_SPLIT,
            validation_fraction=_TEST_VALIDATION_FRACTION_SPLIT,
            test_fraction=_TEST_TEST_FRACTION_SPLIT,
        )

        true_managed_model = gca_model.Model(display_name=_TEST_MODEL_DISPLAY_NAME)

        true_input_data_config = gca_training_pipeline.InputDataConfig(
            fraction_split=true_fraction_split,
            predefined_split=gca_training_pipeline.PredefinedSplit(
                key=_TEST_PREDEFINED_SPLIT_COLUMN_NAME
            ),
            dataset_id=mock_dataset_tabular.name,
        )

        true_training_pipeline = gca_training_pipeline.TrainingPipeline(
            display_name=_TEST_DISPLAY_NAME,
            training_task_definition=schema.training_job.definition.tabular_task,
            training_task_inputs=_TEST_TRAINING_TASK_INPUTS,
            model_to_upload=true_managed_model,
            input_data_config=true_input_data_config,
        )

        mock_pipeline_service_create.assert_called_once_with(
            parent=initializer.global_config.common_location_path(),
            training_pipeline=true_training_pipeline,
        )

        assert job._gca_resource is mock_pipeline_service_create.return_value

        mock_model_service_get.assert_called_once_with(name=_TEST_MODEL_NAME)

        assert model_from_job._gca_resource is mock_model_service_get.return_value

        assert job.get_model()._gca_resource is mock_model_service_get.return_value

        assert not job.has_failed

        assert job.state == gca_pipeline_state.PipelineState.PIPELINE_STATE_SUCCEEDED

    def test_run_call_pipeline_if_no_model_display_name(
        self,
        mock_pipeline_service_create,
        mock_dataset_tabular,
        mock_model_service_get,
    ):
        aiplatform.init(project=_TEST_PROJECT, staging_bucket=_TEST_BUCKET_NAME)

        job = AutoMLTabularTrainingJob(
            display_name=_TEST_DISPLAY_NAME,
            optimization_objective=_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
            optimization_prediction_type=_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
            column_transformations=_TEST_TRAINING_COLUMN_TRANSFORMATIONS,
            optimization_objective_recall_value=None,
            optimization_objective_precision_value=None,
        )

        _ = job.run(
            dataset=mock_dataset_tabular,
            target_column=_TEST_TRAINING_TARGET_COLUMN,
            training_fraction_split=_TEST_TRAINING_FRACTION_SPLIT,
            validation_fraction_split=_TEST_VALIDATION_FRACTION_SPLIT,
            test_fraction_split=_TEST_TEST_FRACTION_SPLIT,
            weight_column=_TEST_TRAINING_WEIGHT_COLUMN,
            budget_milli_node_hours=_TEST_TRAINING_BUDGET_MILLI_NODE_HOURS,
            disable_early_stopping=_TEST_TRAINING_DISABLE_EARLY_STOPPING,
        )

        true_fraction_split = gca_training_pipeline.FractionSplit(
            training_fraction=_TEST_TRAINING_FRACTION_SPLIT,
            validation_fraction=_TEST_VALIDATION_FRACTION_SPLIT,
            test_fraction=_TEST_TEST_FRACTION_SPLIT,
        )

        # Test that if defaults to the job display name
        true_managed_model = gca_model.Model(display_name=_TEST_DISPLAY_NAME)

        true_input_data_config = gca_training_pipeline.InputDataConfig(
            fraction_split=true_fraction_split, dataset_id=mock_dataset_tabular.name,
        )

        true_training_pipeline = gca_training_pipeline.TrainingPipeline(
            display_name=_TEST_DISPLAY_NAME,
            training_task_definition=schema.training_job.definition.tabular_task,
            training_task_inputs=_TEST_TRAINING_TASK_INPUTS,
            model_to_upload=true_managed_model,
            input_data_config=true_input_data_config,
        )

        mock_pipeline_service_create.assert_called_once_with(
            parent=initializer.global_config.common_location_path(),
            training_pipeline=true_training_pipeline,
        )

    def test_run_called_predefined_split_nontabular_raises(
        self,
        mock_pipeline_service_create,
        mock_dataset_nontabular,
        mock_model_service_get,
    ):
        aiplatform.init(project=_TEST_PROJECT, staging_bucket=_TEST_BUCKET_NAME)

        job = AutoMLTabularTrainingJob(
            display_name=_TEST_DISPLAY_NAME,
            optimization_prediction_type=_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
            optimization_objective=_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
            column_transformations=_TEST_TRAINING_COLUMN_TRANSFORMATIONS,
            optimization_objective_recall_value=None,
            optimization_objective_precision_value=None,
        )

        with pytest.raises(ValueError):
            job.run(
                dataset=mock_dataset_nontabular,
                target_column=_TEST_TRAINING_TARGET_COLUMN,
                model_display_name=_TEST_MODEL_DISPLAY_NAME,
                training_fraction_split=_TEST_TRAINING_FRACTION_SPLIT,
                validation_fraction_split=_TEST_VALIDATION_FRACTION_SPLIT,
                test_fraction_split=_TEST_TEST_FRACTION_SPLIT,
                predefined_split_column_name=_TEST_PREDEFINED_SPLIT_COLUMN_NAME,
            )

    def test_run_called_twice_raises(
        self,
        mock_pipeline_service_create,
        mock_dataset_tabular,
        mock_model_service_get,
    ):
        aiplatform.init(project=_TEST_PROJECT, staging_bucket=_TEST_BUCKET_NAME)

        job = AutoMLTabularTrainingJob(
            display_name=_TEST_DISPLAY_NAME,
            optimization_prediction_type=_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
            optimization_objective=_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
            column_transformations=_TEST_TRAINING_COLUMN_TRANSFORMATIONS,
            optimization_objective_recall_value=None,
            optimization_objective_precision_value=None,
        )

        job.run(
            dataset=mock_dataset_tabular,
            target_column=_TEST_TRAINING_TARGET_COLUMN,
            model_display_name=_TEST_MODEL_DISPLAY_NAME,
            training_fraction_split=_TEST_TRAINING_FRACTION_SPLIT,
            validation_fraction_split=_TEST_VALIDATION_FRACTION_SPLIT,
            test_fraction_split=_TEST_TEST_FRACTION_SPLIT,
        )

        with pytest.raises(RuntimeError):
            job.run(
                dataset=mock_dataset_tabular,
                target_column=_TEST_TRAINING_TARGET_COLUMN,
                model_display_name=_TEST_MODEL_DISPLAY_NAME,
                training_fraction_split=_TEST_TRAINING_FRACTION_SPLIT,
                validation_fraction_split=_TEST_VALIDATION_FRACTION_SPLIT,
                test_fraction_split=_TEST_TEST_FRACTION_SPLIT,
            )

    def test_run_call_pipeline_service_create_with_no_dataset(
        self, mock_pipeline_service_create, mock_model_service_get,
    ):
        aiplatform.init(project=_TEST_PROJECT, staging_bucket=_TEST_BUCKET_NAME)

        job = AutoMLTabularTrainingJob(
            display_name=_TEST_DISPLAY_NAME,
            optimization_prediction_type=_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
            optimization_objective=_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
            column_transformations=_TEST_TRAINING_COLUMN_TRANSFORMATIONS,
            optimization_objective_recall_value=None,
            optimization_objective_precision_value=None,
        )

        model_from_job = job.run(
            dataset=None,
            target_column=_TEST_TRAINING_TARGET_COLUMN,
            training_fraction_split=_TEST_TRAINING_FRACTION_SPLIT,
            validation_fraction_split=_TEST_VALIDATION_FRACTION_SPLIT,
            test_fraction_split=_TEST_TEST_FRACTION_SPLIT,
            weight_column=_TEST_TRAINING_WEIGHT_COLUMN,
            budget_milli_node_hours=_TEST_TRAINING_BUDGET_MILLI_NODE_HOURS,
            model_display_name=_TEST_MODEL_DISPLAY_NAME,
            disable_early_stopping=_TEST_TRAINING_DISABLE_EARLY_STOPPING,
        )

        true_managed_model = gca_model.Model(display_name=_TEST_MODEL_DISPLAY_NAME)

        true_training_pipeline = gca_training_pipeline.TrainingPipeline(
            display_name=_TEST_DISPLAY_NAME,
            training_task_definition=schema.training_job.definition.tabular_task,
            training_task_inputs=_TEST_TRAINING_TASK_INPUTS,
            model_to_upload=true_managed_model,
            input_data_config=None,
        )

        mock_pipeline_service_create.assert_called_once_with(
            parent=initializer.global_config.common_location_path(),
            training_pipeline=true_training_pipeline,
        )

        assert job._gca_resource is mock_pipeline_service_create.return_value

        mock_model_service_get.assert_called_once_with(name=_TEST_MODEL_NAME)

        assert model_from_job._gca_resource is mock_model_service_get.return_value

    def test_run_returns_none_if_no_model_to_upload(
        self,
        mock_pipeline_service_create_with_no_model_to_upload,
        mock_dataset_tabular,
    ):
        aiplatform.init(project=_TEST_PROJECT, staging_bucket=_TEST_BUCKET_NAME)

        job = AutoMLTabularTrainingJob(
            display_name=_TEST_DISPLAY_NAME,
            optimization_prediction_type=_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
            optimization_objective=_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
            column_transformations=_TEST_TRAINING_COLUMN_TRANSFORMATIONS,
            optimization_objective_recall_value=None,
            optimization_objective_precision_value=None,
        )

        model = job.run(
            model_display_name=_TEST_MODEL_DISPLAY_NAME,
            dataset=mock_dataset_tabular,
            target_column=_TEST_TRAINING_TARGET_COLUMN,
            training_fraction_split=_TEST_TRAINING_FRACTION_SPLIT,
            validation_fraction_split=_TEST_VALIDATION_FRACTION_SPLIT,
            test_fraction_split=_TEST_TEST_FRACTION_SPLIT,
        )

        assert model is None

    def test_get_model_raises_if_no_model_to_upload(
        self,
        mock_pipeline_service_create_with_no_model_to_upload,
        mock_dataset_tabular,
    ):
        aiplatform.init(project=_TEST_PROJECT, staging_bucket=_TEST_BUCKET_NAME)

        job = AutoMLTabularTrainingJob(
            display_name=_TEST_DISPLAY_NAME,
            optimization_prediction_type=_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
            optimization_objective=_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
            column_transformations=_TEST_TRAINING_COLUMN_TRANSFORMATIONS,
            optimization_objective_recall_value=None,
            optimization_objective_precision_value=None,
        )

        job.run(
            model_display_name=_TEST_MODEL_DISPLAY_NAME,
            dataset=mock_dataset_tabular,
            target_column=_TEST_TRAINING_TARGET_COLUMN,
            training_fraction_split=_TEST_TRAINING_FRACTION_SPLIT,
            validation_fraction_split=_TEST_VALIDATION_FRACTION_SPLIT,
            test_fraction_split=_TEST_TEST_FRACTION_SPLIT,
        )

        with pytest.raises(RuntimeError):
            job.get_model()

    def test_run_raises_if_pipeline_fails(
        self, mock_pipeline_service_create_and_get_with_fail, mock_dataset_tabular,
    ):

        aiplatform.init(project=_TEST_PROJECT, staging_bucket=_TEST_BUCKET_NAME)

        job = AutoMLTabularTrainingJob(
            display_name=_TEST_DISPLAY_NAME,
            optimization_prediction_type=_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
            optimization_objective=_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
            column_transformations=_TEST_TRAINING_COLUMN_TRANSFORMATIONS,
            optimization_objective_recall_value=None,
            optimization_objective_precision_value=None,
        )

        with pytest.raises(RuntimeError):
            job.run(
                model_display_name=_TEST_MODEL_DISPLAY_NAME,
                dataset=mock_dataset_tabular,
                target_column=_TEST_TRAINING_TARGET_COLUMN,
                training_fraction_split=_TEST_TRAINING_FRACTION_SPLIT,
                validation_fraction_split=_TEST_VALIDATION_FRACTION_SPLIT,
                test_fraction_split=_TEST_TEST_FRACTION_SPLIT,
            )

        with pytest.raises(RuntimeError):
            job.get_model()

    def test_raises_before_run_is_called(self, mock_pipeline_service_create):
        aiplatform.init(project=_TEST_PROJECT, staging_bucket=_TEST_BUCKET_NAME)

        job = AutoMLTabularTrainingJob(
            display_name=_TEST_DISPLAY_NAME,
            optimization_prediction_type=_TEST_TRAINING_OPTIMIZATION_PREDICTION_TYPE,
            optimization_objective=_TEST_TRAINING_OPTIMIZATION_OBJECTIVE_NAME,
            column_transformations=_TEST_TRAINING_COLUMN_TRANSFORMATIONS,
            optimization_objective_recall_value=None,
            optimization_objective_precision_value=None,
        )

        with pytest.raises(RuntimeError):
            job.get_model()

        with pytest.raises(RuntimeError):
            job.has_failed

        with pytest.raises(RuntimeError):
            job.state