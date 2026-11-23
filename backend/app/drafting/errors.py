class DraftProblem(Exception):
    def __init__(self,status,code,message,current_revision=None):
        self.status=status;self.code=code;self.message=message;self.current_revision=current_revision
        super().__init__(message)
