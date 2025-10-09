from datetime import datetime
#
# dr = '16:30:52'
# print(dr.split(':'))
#
# from datetime import datetime, time
# import time
#
data = [
    {'event__id': 21, 'event__training_type': '🏀 Баскетбол', 'event__participants_count': 3,
     'event__stars': '3, 33', 'user_id': 15,
     'created_at': datetime(2025, 10, 4, 21, 17, 50, 152814)},

    {'event__id': 21, 'event__training_type': '🏀 Баскетбол', 'event__participants_count': 3, 'event__stars': '3, 33',
     'user_id': 3, 'created_at': datetime(2025, 10, 4, 20, 59, 40, 491610)},

    {'event__id': 27, 'event__training_type': '⚽️ Футбол', 'event__participants_count': 12, 'event__stars': None, 'user_id': 3,
     'created_at': datetime(2025, 10, 4, 21, 39, 18, 101711)},

    {'event__id': 23, 'event__training_type': '🏸 Бадминтон', 'event__participants_count': 5, 'event__stars': None,
     'user_id': 33,
     'created_at': datetime(2025, 10, 4, 21, 40, 21, 218945)},

    {'event__id': 25, 'event__training_type': '🏐 Волейбол', 'event__participants_count': 12, 'event__stars': None,
     'user_id': 32,
     'created_at': datetime(2025, 10, 4, 23, 26, 53, 897345)},

    {'event__id': 21, 'event__training_type': '🏀 Баскетбол', 'event__participants_count': 3, 'event__stars': '3, 33',
     'user_id': 34, 'created_at': datetime(2025, 10, 4, 23, 27, 23, 338493)},

    {'event__id': 26, 'event__training_type': '⚽️ Футбол', 'event__participants_count': 1, 'event__stars': None,
     'user_id': 32, 'created_at': datetime(2025, 10, 5, 8, 4, 53, 588305)},

    {'event__id': 21, 'event__training_type': '🏀 Баскетбол', 'event__participants_count': 3, 'event__stars': '3, 33',
     'user_id': 33, 'created_at': datetime(2025, 10, 5, 8, 9, 11, 957247)},

    {'event__id': 26, 'event__training_type': '⚽️ Футбол', 'event__participants_count': 1, 'event__stars': None,
     'user_id': 3, 'created_at': datetime(2025, 10, 5, 8, 32, 8, 442235)},

    {'event__id': 21, 'event__training_type': '🏀 Баскетбол', 'event__participants_count': 3, 'event__stars': '3, 33',
     'user_id': 32, 'created_at': datetime(2025, 10, 5, 8, 33, 12, 129667)},

    {'event__id': 27, 'event__training_type': '⚽️ Футбол', 'event__participants_count': 12, 'event__stars': None,
     'user_id': 32, 'created_at': datetime(2025, 10, 5, 9, 8, 2, 455586)},

    {'event__id': 22, 'event__training_type': '🏐 Волейбол', 'event__participants_count': 12, 'event__stars': None,
     'user_id': 32, 'created_at': datetime(2025, 10, 5, 9, 9, 7, 794638)},

    {'event__id': 23, 'event__training_type': '🏸 Бадминтон', 'event__participants_count': 5, 'event__stars': None,
     'user_id': 32, 'created_at': datetime(2025, 10, 5, 9, 11, 5, 850126)},

    {'event__id': 24, 'event__training_type': '🏸 Бадминтон', 'event__participants_count': 12, 'event__stars': None,
     'user_id': 32, 'created_at': datetime(2025, 10, 5, 9, 20, 5, 923199)},

    {'event__id': 24, 'event__training_type': '🏸 Бадминтон', 'event__participants_count': 12, 'event__stars': None,
     'user_id': 33, 'created_at': datetime(2025, 10, 5, 9, 21, 25, 445852)}
]

a = '⛔️'
print(3*a)


# _slr = "1,  2   ,  3  "
# lst = _slr.replace(' ','').split(',')
# print(f'lst={lst}')
# tpl = tuple(map(lambda x: int(x), lst))
# print(f'tpl={tpl}')
#
# # Формируем множество звезд
# stars = {
#     (
#         item['event__training_type'],
#         tuple(map(lambda x: int(x), item['event__stars'].replace(' ', '').split(','))),
#         item['event__id']
#     )
#     for item in data if item['event__stars'] is not None
# }
# print(f'stars = {stars}')
#
# # Формируем список списков, растасованных по event_id
# general_list = []
# for event_id in {item['event__id'] for item in data}:
#     lst = sorted([_item for _item in data if _item['event__id'] == event_id], key=lambda x: x['created_at'])
#
#     ''' Находим крайний индекс основного списка участников тренировки по первому элементу'''
#     last_index = lst[0]['event__participants_count']
#     general_list.append(lst[:last_index])
#
# for item in general_list:
#     for _item in item:
#         print(f'event_id: {_item["event__id"]}; created_at: {_item["created_at"]}; '
#               f'уяастники: {_item["event__participants_count"]}')
#
# lst = [1,2,1,5,6,5,6,8,8,9,4,5]
# ss = set()
# ss.add(9)
# ss.add(89)
# print(ss)

#
# star_dict = []  # список словарей звезд тренировок
# for event_id in data:
#
#     if event_id['event__stars'] is not None:
#         if len(event_id['event__stars']) >0:
#             _stars = tuple(map(lambda x: int(x), event_id['event__stars'].replace(' ', '').split(',')))
#
#             dct = {'training_type': event_id['event__training_type'],
#     'stars':event_id['event__stars'] , 'event':}
#
#
# training_types = {(item['event__training_type'], item['event__id'],
#                    tuple(map(lambda x: int(x), item['event__stars'].replace(' ','').split(','))))
#                   for item in data if item['event__id']>1}
# # star_list = {iv}
# # print(training_types)
# a='1,2,23'
# print(a.split(','))
#
#
# statistics = [{'user_id': 23, 'season_index': 0, 'training_type': '🏸 Бадминтон'},
#               {'user_id': 33, 'season_index': 0, 'training_type': '🏀 Баскетбол'}]
#
# # sort_lst = sorted(data, key=lambda k: k['event__id'])
# # init_lst = [item['event__id'] for item in data]
# # sort_lst = [item['event__id'] for item in sort_general_lst]
# # #
# # print(f'training_types = {training_types}')
# # #
# # #
# # # event_ids_list = []
# # # ''' Формируется множество из event_id, и затем по нему вызывается цикл '''
# # # for i in {item['event__id'] for item in data if item['event__id']==21}:
# # #     ''' Растасовываем словари event по отдельным спискам '''
# # #     lst=[item_ for i_, item_ in enumerate(data) if item_['event__id'] == i]
# # #     ''' Сортируем участников по времени добавления и отсекаем резерв '''
# # #     last_index = lst[0]['event__participants_count']  # крацний индекс основного списка для отсечения резерва
# # #     sorted_lst = sorted(lst, key=lambda x: x['created_at'])[:last_index]
# # #
# # #     for _i in range(len(sorted_lst)):
# # #         print(f'до сортировки: {lst[_i]['created_at'].strftime('%d.%m.%Y  %H:%M')};   '
# # #               f'после сортировки: {sorted_lst[_i]['created_at'].strftime('%d.%m.%Y  %H:%M')}')
# # #
# # #     print(f'усеченно-отсортированный список: : {sorted_lst}')
# # #     for _i in sorted_lst:
# # #         print(_i)
# # #
# # #
# # # ds = [1,2,55,23,2,55,23,1,2,6]
# # # ds_1 = [12,55,23,2,5,2,6]
# # # print(set(ds) - set(ds_1))
# # # # print (f'время = {time.time() - start}')
# # # #
# # # # [{'id': 21, 'training_type': '🏀 Баскетбол', 'participants_count': 3, 'stars': '3, 33', 'user__id': 15, 'created_at': datetime(2025, 2, 7, 13, 28, 16, 964619)}, {'id': 21, 'training_type': '🏀 Баскетбол', 'participants_count': 3, 'stars': '3, 33', 'user__id': 33, 'created_at': datetime(2025, 6, 2, 16, 55, 14, 363460)}, {'id': 21, 'training_type': '🏀 Баскетбол', 'participants_count': 3, 'stars': '3, 33', 'user__id': 32, 'created_at': datetime(2025, 5, 8, 23, 14, 16, 772303)}]
# # # # [{'id': 21, 'training_type': '🏀 Баскетбол', 'participants_count': 3, 'stars': '3, 33', 'user__id': 15, 'created_at': datetime(2025, 2, 7, 13, 28, 16, 964619)}, {'id': 21, 'training_type': '🏀 Баскетбол', 'participants_count': 3, 'stars': '3, 33', 'user__id': 32, 'created_at': datetime(2025, 5, 8, 23, 14, 16, 772303)}, {'id': 21, 'training_type': '🏀 Баскетбол', 'participants_count': 3, 'stars': '3, 33', 'user__id': 33, 'created_at': datetime(2025, 6, 2, 16, 55, 14, 363460)}]

