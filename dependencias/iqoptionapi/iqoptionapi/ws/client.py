"""Module for IQ option websocket."""

import json
import logging
import websocket
import iqoptionapi.constants as OP_code
import iqoptionapi.global_value as global_value
from threading import Thread
from iqoptionapi.ws.received.technical_indicators import technical_indicators
from iqoptionapi.ws.received.time_sync import time_sync
from iqoptionapi.ws.received.heartbeat import heartbeat
from iqoptionapi.ws.received.balances import balances
from iqoptionapi.ws.received.profile import profile
from iqoptionapi.ws.received.balance_changed import balance_changed
from iqoptionapi.ws.received.candles import candles
from iqoptionapi.ws.received.buy_complete import buy_complete
from iqoptionapi.ws.received.option import option
from iqoptionapi.ws.received.position_history import position_history
from iqoptionapi.ws.received.list_info_data import list_info_data
from iqoptionapi.ws.received.candle_generated import candle_generated_realtime
from iqoptionapi.ws.received.candle_generated_v2 import candle_generated_v2
from iqoptionapi.ws.received.commission_changed import commission_changed
from iqoptionapi.ws.received.socket_option_opened import socket_option_opened
from iqoptionapi.ws.received.api_option_init_all_result import api_option_init_all_result
from iqoptionapi.ws.received.initialization_data import initialization_data
from iqoptionapi.ws.received.underlying_list import underlying_list
from iqoptionapi.ws.received.instruments import instruments
from iqoptionapi.ws.received.financial_information import financial_information
from iqoptionapi.ws.received.position_changed import position_changed
from iqoptionapi.ws.received.option_opened import option_opened
from iqoptionapi.ws.received.option_closed import option_closed
from iqoptionapi.ws.received.top_assets_updated import top_assets_updated
from iqoptionapi.ws.received.strike_list import strike_list
from iqoptionapi.ws.received.api_game_betinfo_result import api_game_betinfo_result
from iqoptionapi.ws.received.traders_mood_changed import traders_mood_changed
from iqoptionapi.ws.received.order import order
from iqoptionapi.ws.received.position import position
from iqoptionapi.ws.received.positions import positions
from iqoptionapi.ws.received.order_placed_temp import order_placed_temp
from iqoptionapi.ws.received.deferred_orders import deferred_orders
from iqoptionapi.ws.received.history_positions import history_positions
from iqoptionapi.ws.received.available_leverages import available_leverages
from iqoptionapi.ws.received.order_canceled import order_canceled
from iqoptionapi.ws.received.position_closed import position_closed
from iqoptionapi.ws.received.overnight_fee import overnight_fee
from iqoptionapi.ws.received.api_game_getoptions_result import api_game_getoptions_result
from iqoptionapi.ws.received.sold_options import sold_options
from iqoptionapi.ws.received.tpsl_changed import tpsl_changed
from iqoptionapi.ws.received.auto_margin_call_changed import auto_margin_call_changed
from iqoptionapi.ws.received.digital_option_placed import digital_option_placed
from iqoptionapi.ws.received.result import result
from iqoptionapi.ws.received.instrument_quotes_generated import instrument_quotes_generated
from iqoptionapi.ws.received.training_balance_reset import training_balance_reset
from iqoptionapi.ws.received.socket_option_closed import socket_option_closed
from iqoptionapi.ws.received.live_deal_binary_option_placed import live_deal_binary_option_placed
from iqoptionapi.ws.received.live_deal_digital_option import live_deal_digital_option
from iqoptionapi.ws.received.leaderboard_deals_client import leaderboard_deals_client
from iqoptionapi.ws.received.live_deal import live_deal
from iqoptionapi.ws.received.user_profile_client import user_profile_client
from iqoptionapi.ws.received.leaderboard_userinfo_deals_client import leaderboard_userinfo_deals_client
from iqoptionapi.ws.received.client_price_generated import client_price_generated
from iqoptionapi.ws.received.users_availability import users_availability


class WebsocketClient(object):
    """Class for work with IQ option websocket."""

    def __init__(self, api):
        """
        :param api: The instance of :class:`IQOptionAPI
            <iqoptionapi.api.IQOptionAPI>`.
        """
        self.api = api
        
        # Adicionar headers e cookies semelhantes a um navegador real
        extra_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Origin": "https://iqoption.com",
            "Upgrade": "websocket"
        }
        
        # Incluir cookies da sessão nos headers
        cookie_str = "; ".join([f"{k}={v}" for k, v in self.api.session.cookies.get_dict().items()])
        if cookie_str:
            extra_headers["Cookie"] = cookie_str
            
        self.wss = websocket.WebSocketApp(
            self.api.wss_url, 
            on_message=self.on_message,
            on_error=self.on_error, 
            on_close=self.on_close,
            on_open=self.on_open,
            header=extra_headers
        )

    def dict_queue_add(self, dict, maxdict, key1, key2, key3, value):
        if key3 in dict[key1][key2]:
            dict[key1][key2][key3] = value
        else:
            while True:
                try:
                    dic_size = len(dict[key1][key2])
                except:
                    dic_size = 0
                if dic_size < maxdict:
                    dict[key1][key2][key3] = value
                    break
                else:
                    # del mini key
                    del dict[key1][key2][sorted(
                        dict[key1][key2].keys(), reverse=False)[0]]

    def api_dict_clean(self, obj):
        if len(obj) > 5000:
            for k in obj.keys():
                del obj[k]
                break

    def on_message(self, websocket, message):  # pylint: disable=unused-argument
        """Method to process websocket messages."""
        global_value.ssl_Mutual_exclusion = True
        logger = logging.getLogger(__name__)
        
        # ----- Verificações Iniciais ----- #
        if message is None:
            logger.warning("Mensagem nula recebida do WebSocket")
            global_value.ssl_Mutual_exclusion = False
            return
            
        # Assegurar que a mensagem é uma string para manipulação segura
        if not isinstance(message, str):
            try:
                # Tentar decodificar bytes para string (UTF-8 padrão)
                message = message.decode('utf-8')
            except (UnicodeDecodeError, AttributeError) as decode_error:
                logger.warning(f"Mensagem não decodificável recebida: {decode_error}. Tipo: {type(message)}")
                global_value.ssl_Mutual_exclusion = False
                return

        # Remover espaços em branco no início e fim
        message = message.strip()
        
        # Verificar se a mensagem está vazia após strip
        if not message:
            logger.warning("Mensagem vazia (após strip) recebida do WebSocket")
            global_value.ssl_Mutual_exclusion = False
            return
            
        # Verificar se é uma mensagem JSON válida (começa com { ou [)
        if not message.startswith(("{", "[")):
            logger.debug(f"Mensagem não-JSON recebida e ignorada: '{message[:100]}...'")
            global_value.ssl_Mutual_exclusion = False
            return
            
        # ----- Processamento JSON ----- #
        # Log para debug
        if len(message) < 1000:
            logger.debug(f"Processando mensagem: {message}")
        else:
            logger.debug(f"Processando mensagem grande: {message[:200]}... (truncada)")

        try:
            # Converter a mensagem para JSON
            message_json = json.loads(message) # Usar 'message' já tratada
            
            # Registrar o tipo de mensagem para diagnóstico
            if "name" in message_json:
                logger.debug(f"Tipo da mensagem: {message_json['name']}")
                        
            # Processa a mensagem conforme o tipo (código existente)
            technical_indicators(self.api, message_json, self.api_dict_clean)
            time_sync(self.api, message_json)
            heartbeat(self.api, message_json)
            balances(self.api, message_json)
            profile(self.api, message_json)
            balance_changed(self.api, message_json)
            candles(self.api, message_json)
            buy_complete(self.api, message_json)
            option(self.api, message_json)
            position_history(self.api, message_json)
            list_info_data(self.api, message_json)
            candle_generated_realtime(self.api, message_json, self.dict_queue_add)
            candle_generated_v2(self.api, message_json, self.dict_queue_add)
            commission_changed(self.api, message_json)
            socket_option_opened(self.api, message_json)
            api_option_init_all_result(self.api, message_json)
            initialization_data(self.api, message_json)
            underlying_list(self.api, message_json)
            instruments(self.api, message_json)
            financial_information(self.api, message_json)
            position_changed(self.api, message_json)
            option_opened(self.api, message_json)
            option_closed(self.api, message_json)
            top_assets_updated(self.api, message_json)
            strike_list(self.api, message_json)
            api_game_betinfo_result(self.api, message_json)
            traders_mood_changed(self.api, message_json)
             # ------for forex&cfd&crypto..
            order_placed_temp(self.api, message_json)
            order(self.api, message_json)
            position(self.api, message_json)
            positions(self.api, message_json)
            order_placed_temp(self.api, message_json)
            deferred_orders(self.api, message_json)
            history_positions(self.api, message_json)
            available_leverages(self.api, message_json)
            order_canceled(self.api, message_json)
            position_closed(self.api, message_json)
            overnight_fee(self.api, message_json)
            api_game_getoptions_result(self.api, message_json)
            sold_options(self.api, message_json)
            tpsl_changed(self.api, message_json)
            auto_margin_call_changed(self.api, message_json)
            digital_option_placed(self.api, message_json, self.api_dict_clean)
            result(self.api, message_json)
            instrument_quotes_generated(self.api, message_json)
            training_balance_reset(self.api, message_json)
            socket_option_closed(self.api, message_json)
            live_deal_binary_option_placed(self.api, message_json)
            live_deal_digital_option(self.api, message_json)
            leaderboard_deals_client(self.api, message_json)
            live_deal(self.api, message_json)
            user_profile_client(self.api, message_json)
            leaderboard_userinfo_deals_client(self.api, message_json)
            users_availability(self.api, message_json)
            client_price_generated(self.api, message_json)
            
        except json.JSONDecodeError as e:
            # Esta exceção agora deve ser mais rara com as verificações acima
            logger.error(f"Erro ao decodificar mensagem JSON (mesmo após verificações): {e}")
            logger.debug(f"Mensagem problemática: {message[:100]}...")
        except KeyError as e:
            logger.error(f"Erro de chave ao processar mensagem JSON: {e}")
            logger.debug(f"Mensagem JSON com formato inesperado: {message_json}")
        except Exception as e:
            logger.error(f"Erro não esperado ao processar mensagem: {str(e)}")
            import traceback
            logger.debug(f"Detalhes do erro: {traceback.format_exc()}")
            
        global_value.ssl_Mutual_exclusion = False

    @staticmethod
    def on_error(websocket, error):  # pylint: disable=unused-argument
        """Method to process websocket errors."""
        logger = logging.getLogger(__name__)
        logger.error(error)
        global_value.websocket_error_reason = str(error)
        global_value.check_websocket_if_error = True

    @staticmethod
    def on_open(websocket):  # pylint: disable=unused-argument
        """Method to process websocket open."""
        logger = logging.getLogger(__name__)
        logger.debug("Websocket client connected.")
        global_value.check_websocket_if_connect = 1

    @staticmethod
    def on_close(websocket, close_status_code, close_msg):  # pylint: disable=unused-argument
        """Method to process websocket close."""
        logger = logging.getLogger(__name__)
        logger.debug("Websocket connection closed.")
        global_value.check_websocket_if_connect = 0
