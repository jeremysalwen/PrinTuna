from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Union

import optuna
from optuna._experimental import experimental
from optuna._imports import try_import
from optuna.study.study import ObjectiveFuncType


with try_import() as _imports:
    import mlflow

RUN_ID_ATTRIBUTE_KEY = "mlflow_run_id"


@experimental("1.4.0")
class MLflowCallback(object):
    """Callback to track Optuna trials with MLflow.

    This callback adds relevant information that is
    tracked by Optuna to MLflow. The MLflow experiment
    will be named after the Optuna study name.

    Example:

        Add MLflow callback to Optuna optimization.

        .. testsetup::

            import pathlib
            import tempfile

            tempdir = tempfile.mkdtemp()
            YOUR_TRACKING_URI = pathlib.Path(tempdir).as_uri()

        .. testcode::

            import optuna
            from optuna.integration.mlflow import MLflowCallback


            def objective(trial):
                x = trial.suggest_float("x", -10, 10)
                return (x - 2) ** 2


            mlflc = MLflowCallback(
                tracking_uri=YOUR_TRACKING_URI,
                metric_name="my metric score",
            )

            study = optuna.create_study(study_name="my_study")
            study.optimize(objective, n_trials=10, callbacks=[mlflc])

        .. testcleanup::

            import shutil

            shutil.rmtree(tempdir)

        .. testoutput::
            :hide:
            :options: +NORMALIZE_WHITESPACE

            INFO: 'my_study' does not exist. Creating a new experiment

        Add additional logging to MLflow

        .. testcode::

            import optuna
            import mlflow
            from optuna.integration.mlflow import MLflowCallback

            mlflc = MLflowCallback(
                tracking_uri=YOUR_TRACKING_URI,
                metric_name="my metric score",
            )


            @mlflc.track_in_mlflow()
            def objective(trial):
                x = trial.suggest_float("x", -10, 10)
                mlflow.log_param("power", 2)
                mlflow.log_metric("base of metric", x - 2)

                return (x - 2) ** 2


            study = optuna.create_study(study_name="my_other_study")
            study.optimize(objective, n_trials=10, callbacks=[mlflc])


        .. testoutput::
            :hide:
            :options: +NORMALIZE_WHITESPACE

            INFO: 'my_other_study' does not exist. Creating a new experiment

    Args:
        tracking_uri:
            The URI of the MLflow tracking server.

            Please refer to `mlflow.set_tracking_uri
            <https://www.mlflow.org/docs/latest/python_api/mlflow.html#mlflow.set_tracking_uri>`_
            for more details.
        metric_name:
            Name assigned to optimized metric. In case of multi-objective optimization,
            list of names can be passed. Those names will be assigned
            to metrics in the order returned by objective function.
            If single name is provided, or this argument is left to default value,
            it will be broadcasted to each objective with a number suffix in order
            returned by objective function e.g. two objectives and default metric name
            will be logged as ``value_0`` and ``value_1``.
        nest_trials:
            Flag indicating whether or not trials should be logged as
            nested runs. This is often helpful for aggregating trials
            to a particular study, under a given experiment.
        tag_study_user_attrs:
            Flag indicating whether or not to add the study's user attrs
            to the mlflow trial as tags. Please note that when this flag is
            set, key value pairs in :attr:`~optuna.study.Study.user_attrs`
            will supersede existing tags.
    """

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        metric_name: Union[str, Sequence[str]] = "value",
        nest_trials: bool = False,
        tag_study_user_attrs: bool = False,
    ) -> None:

        _imports.check()

        if not isinstance(metric_name, Sequence):
            raise TypeError(
                "Expected metric_name to be string or sequence of strings, got {}.".format(
                    type(metric_name)
                )
            )

        self._tracking_uri = tracking_uri
        self._metric_name = metric_name
        self._nest_trials = nest_trials
        self._tag_study_user_attrs = tag_study_user_attrs

    def __call__(self, study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:

        self._initialize_experiment(study)

        with mlflow.start_run(
            run_id=trial.system_attrs.get(RUN_ID_ATTRIBUTE_KEY),
            run_name=str(trial.number),
            nested=self._nest_trials,
        ):

            # This sets the metrics for MLflow.
            self._log_metrics(trial.values)

            # This sets the params for MLflow.
            self._log_params(trial.params)

            # This sets the tags for MLflow.
            self._set_tags(trial, study)

    @experimental("2.9.0")
    def track_in_mlflow(self) -> Callable:
        """Decorator for using MLflow logging in the objective function.

        This decorator enables the extension of MLflow logging provided by the callback.

        All information logged in the decorated objective function will be added to the MLflow
        run for the trial created by the callback.

        Returns:
            ObjectiveFuncType: Objective function with tracking to MLflow enabled.
        """

        def decorator(func: ObjectiveFuncType) -> ObjectiveFuncType:
            def wrapper(trial: optuna.trial.Trial) -> Union[float, Sequence[float]]:
                study = trial.study
                self._initialize_experiment(study)

                with mlflow.start_run(run_name=str(trial.number), nested=self._nest_trials) as run:
                    trial.set_system_attr(RUN_ID_ATTRIBUTE_KEY, run.info.run_id)

                    return func(trial)

            return wrapper

        return decorator

    def _initialize_experiment(self, study: optuna.study.Study) -> None:
        """Initialize an MLflow experiment with the study name.

        If a tracking uri has been provided, MLflow will be initialized to use it.

        Args:
            study: Study to be tracked in MLflow.
        """

        # This sets the `tracking_uri` for MLflow.
        if self._tracking_uri is not None:
            mlflow.set_tracking_uri(self._tracking_uri)

        # This sets the experiment of MLflow.
        mlflow.set_experiment(study.study_name)

    def _set_tags(self, trial: optuna.trial.FrozenTrial, study: optuna.study.Study) -> None:
        """Sets the Optuna tags for the current MLflow run.

        Args:
            trial: Trial to be tracked.
            study: Study to be tracked.
        """

        tags: Dict[str, Union[str, List[str]]] = {}
        tags["number"] = str(trial.number)
        tags["datetime_start"] = str(trial.datetime_start)

        tags["datetime_complete"] = str(trial.datetime_complete)

        # Set trial state.
        if trial.state.is_finished():
            tags["state"] = trial.state.name

        # Set study directions.
        directions = [d.name for d in study.directions]
        tags["direction"] = directions if len(directions) != 1 else directions[0]

        tags.update(trial.user_attrs)
        distributions = {(k + "_distribution"): str(v) for (k, v) in trial.distributions.items()}
        tags.update(distributions)

        if self._tag_study_user_attrs:
            tags.update(study.user_attrs)

        # This is a temporary fix on Optuna side. It avoids an error with user
        # attributes that are too long. It should be fixed on MLflow side later.
        # When it is fixed on MLflow side this codeblock can be removed.
        # see https://github.com/optuna/optuna/issues/1340
        # see https://github.com/mlflow/mlflow/issues/2931
        for key, value in tags.items():
            value = str(value)  # make sure it is a string
            max_val_length = mlflow.utils.validation.MAX_TAG_VAL_LENGTH
            if len(value) > max_val_length:
                tags[key] = "{}...".format(value[: max_val_length - 3])

        # This sets the tags for MLflow.
        mlflow.set_tags(tags)

    def _log_metrics(self, values: List[Union[float, None]]) -> None:
        """Log the trial results as metrics to MLflow.

        Args:
            values: Results of a trial.
        """

        if isinstance(self._metric_name, str):
            if len(values) > 1:
                # Broadcast default name for multi-objective optimization.
                names = ["{}_{}".format(self._metric_name, i) for i in range(len(values))]

            else:
                names = [self._metric_name]

        else:
            if len(self._metric_name) != len(values):
                raise ValueError(
                    "Running multi-objective optimization "
                    "with {} objective values, but {} names specified. "
                    "Match objective values and names, or use default broadcasting.".format(
                        len(values), len(self._metric_name)
                    )
                )

            else:
                names = [*self._metric_name]

        values = [val if val is not None else float("nan") for val in values]
        metrics = {name: val for name, val in zip(names, values)}
        mlflow.log_metrics(metrics)

    @staticmethod
    def _log_params(params: Dict[str, Any]) -> None:
        """Log the parameters of the trial to MLflow.

        Args:
            params: Trial params.
        """

        mlflow.log_params(params)