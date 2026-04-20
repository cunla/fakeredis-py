class BaseModel:
    _model_type: bytes

    @classmethod
    def model_type(cls) -> bytes:
        return cls._model_type
