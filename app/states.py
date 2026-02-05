from aiogram.fsm.state import State, StatesGroup


class CreateUserFSM(StatesGroup):
    account_name = State()
    name = State()

class CreateTrainingTypeFSM(StatesGroup):
    title=State()

class CreateGymFSM(StatesGroup):
    info = State()


class CreateEventFSM(StatesGroup):
    training_type = State()
    template = State()
    save_template = State()
    dedline_type = State()


class AddFriendFSM(StatesGroup):
    add_friend = State()
    add_friend_confirm = State()


class PaymenNotify(StatesGroup):
    confirm = State()


class EditEventFSM(StatesGroup):
    insert_template = State()


class UpdateEventUserFSM(StatesGroup):
    payment_confirmed = State()
    reset_confirmed = State()

class DeleteGymFSM(StatesGroup):
    delete_gym = State()

class DropParticipantFromTrainFSM(StatesGroup):
    waiting = State()
    drop_participant = State()


class ChancelTraininigFSM(StatesGroup):
    chancel_training = State()

class WrightBugsFSM(StatesGroup):
    wright_bug = State()

class EditAdminFSM(StatesGroup):
    show_list = State()
    edit_admin = State()


class EditProfileFSM(StatesGroup):
    show_current_info = State()
    edit_tg_name = State()
    edit_tg_username = State()


class DeleteTemplateFSM(StatesGroup):
    delete_template = State()


class DeleteFromTrainingFSM(StatesGroup):
    delete_from_training = State()


class ChooseEventFSM(StatesGroup):
    training_type = State()
    choose_event = State()
    sign_up_for_training = State()
    admin_management = State()
    give_star = State()
    confirm_give_star = State()


class ShowRaitingFSM(StatesGroup):
    raiting = State()


class SendCheckFSM(StatesGroup):
    send_check = State()


class PayConfirmationFSM(StatesGroup):
    write_participants = State()
