from aiogram.fsm.state import State, StatesGroup


class CreateUserFSM(StatesGroup):
    account_name = State()
    name = State()

class CreateTrainingTypeFSM(StatesGroup):
    title=State()
class CreateGymFSM(StatesGroup):
    info = State()


class CreateEventFSM(StatesGroup):
    template = State()
    save_template = State()
    dedline_type = State()


class UpdateEventUserFSM(StatesGroup):
    payment_confirmed = State()
    reset_confirmed = State()

class DeleteGymFSM(StatesGroup):
    delete_gym = State()

class DropParticipantFromTrainFSM(StatesGroup):
    drop_participant = State()

class ChancelTraininigFSM(StatesGroup):
    chancel_training = State()

class WrightBugsFSM(StatesGroup):
    wright_bug = State()

class EditAdminFSM(StatesGroup):
    edit_admin = State()
