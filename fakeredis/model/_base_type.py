class BaseModel:
    _model_type = None

    @classmethod
    def model_type(cls) -> bytes:
        return cls._model_type
