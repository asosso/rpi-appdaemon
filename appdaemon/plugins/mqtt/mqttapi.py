import appdaemon.adbase as appapi
import appdaemon.utils as utils
import asyncio
import inspect
import traceback


class Entities:

    def __get__(self, instance, owner):
        state = utils.StateAttrs(instance.ad.get_state(instance.namespace, None, None, None))
        return state


class Mqtt(appapi.ADBase):

    entities = Entities()

    def __init__(self, ad, name, logger, error, args, config, app_config, global_vars,):

        super(Mqtt, self).__init__(ad, name, logger, error, args, config, app_config, global_vars)

        self.AD = ad
        self.name = name
        self._logger = logger
        self._error = error
        self.args = args
        self.config = config
        self.app_config = app_config
        self.global_vars = global_vars
        self.loop = self.AD.loop

    #
    # Override listen_state()
    #

    def listen_event(self, cb, event=None, **kwargs):
        namespace = self._get_namespace(**kwargs)

        if 'wildcard' in kwargs:
            wildcard = kwargs['wildcard']
            if wildcard[-2:] == '/#' and len(wildcard.split('/')[0]) >= 1:
                self.AD.get_plugin(namespace).process_mqtt_wildcard(kwargs['wildcard'])
            else:
                self.log("Using {!r} as MQTT Wildcard for Event is not valid, use another. Listen Event will not be registered".format(wildcard), level="WARNING")
                return

        return super(Mqtt, self).listen_event(cb, event, **kwargs)

    #
    # service calls
    #
    def mqtt_publish(self, topic, payload = None, **kwargs):
        kwargs['topic'] = topic
        kwargs['payload'] = payload
        service = 'publish'
        result = self.call_service(service, **kwargs)
        return result

    def mqtt_subscribe(self, topic, **kwargs):
        kwargs['topic'] = topic
        service = 'subscribe'
        result = self.call_service(service, **kwargs)
        return result

    def mqtt_unsubscribe(self, topic, **kwargs):
        kwargs['topic'] = topic
        service = 'unsubscribe'
        result = self.call_service(service, **kwargs)
        return result

    def call_service(self, service, **kwargs):
        self.AD.log(
            "DEBUG",
            "call_service: {}, {}".format(service, kwargs)
        )
        
        namespace = self._get_namespace(**kwargs)

        if 'topic' in kwargs:
            if not self.AD.get_plugin(namespace).active(): #ensure mqtt plugin is connected
                self.log("Attempt to call Mqtt Service while disconnected: {!r}".format(service), level="WARNING")
                return None

            try:
                result = self.AD.get_plugin(namespace).mqtt_service(service, **kwargs)
                
            except Exception as e:
                config = self.AD.get_plugin(namespace).config
                if config['type'] == 'mqtt':
                    self.AD.log('DEBUG', 'Got the following Error {}, when trying to retrieve Mqtt Plugin'.format(e))
                    self.error('Got error with the following {}'.format(e))
                    return str(e)
                else:
                    self.AD.log('CRITICAL', 'Wrong Namespace {!r} selected for MQTT Service. Please use proper namespace before trying again'.format(namespace))
                    self.error('Could not execute Service Call, as wrong Namespace {!r} used'.format(namespace))
                    return 'ERR'
        else:
            self.AD.log('DEBUG', 'Topic not provided for Service Call {!r}.'.format(service))
            raise ValueError("Topic not provided, please provide Topic for Service Call")

        return result
