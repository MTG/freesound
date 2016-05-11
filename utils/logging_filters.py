import logging


class SearchLogsFilter(logging.Filter):

    def filter(self, record):
        message = record.getMessage().encode('utf8')
        if 'Query:' in message:
            record.query = str(message.replace('Query:', ''))
            record.test = unicode("hola")

        return True


class APILogsFilter(logging.Filter):

    def filter(self, record):
        message = record.getMessage().encode('utf8')
        if 'ApiV2' in message:
            # APIV2 message
            record.api_version = 'v2'
            try:
                raw_message = message.split(' <')[0]
                new_message = []
                for part in raw_message.split(' '):
                    if ':' in part:
                        new_message.append(part.split(':')[0])
                    else:
                        new_message.append(part)

                record.api_resource = ' '.join(new_message)
            except:
                record.api_resource = 'unknown'

            try:
                record.api_client_id = message.split('> (')[1].split('Client:')[1].split(')')[0]
            except:
                record.api_client_id = 'unknown'

            try:
                record.api_client_username = message.split('> (')[1].split('Dev:')[1].split(' User:')[0]
            except:
                record.api_client_username = 'unknown'

            try:
                record.api_enduser_username = message.split('> (')[1].split('User:')[1].split(' Client:')[0]
            except:
                record.api_enduser_username = 'unknown'

            try:
                record.api_auth_type = message.split('> (')[1].split('Auth:')[1].split(' Dev:')[0]
            except:
                record.api_auth_type = 'unknown'

        else:
            # APIV1 message
            record.api_version = 'v1'
            try:
                record.api_resource = message.split(',')[0]
            except:
                record.api_resource = 'unknown'

            try:
                record.api_client_key = message.split('api_key=')[1].split(',')[0]
            except:
                record.api_client_key = 'unknown'

            try:
                record.api_client_username = message.split('api_key_username=')[1]
            except:
                record.api_client_username = 'unknown'

        return True


class APIErrorLogsFilter(logging.Filter):
    # Only gets apiv2 error messages

    def filter(self, record):
        message = record.getMessage().encode('utf8')

        if 'ApiV2' in message:
            try:
                record.status = int(message.split(' ')[0][1:])
            except Exception, e:
                record.status = -1

            try:
                record.summary_message = message.split('<')[1].split('>')[0]
            except:
                record.summary_message = 'unknown'

            try:
                record.long_message = message.split('> ')[1].split(' (ApiV2')[0]
            except:
                record.long_message = 'unknown'

            request_info = message[message.rfind('(')+1:-1]
            try:
                record.ip = request_info.split('Ip:')[1]
            except:
                record.ip = 'unknown'
            try:
                record.api_client_id = request_info.split('Client:')[1].split(' Ip:')[0]
            except:
                record.api_client_id = 'unknown'

            try:
                record.api_client_username = request_info.split('Dev:')[1].split(' User:')[0]
            except:
                record.api_client_username = 'unknown'

            try:
                record.api_enduser_username = request_info.split('User:')[1].split(' Client:')[0]
            except:
                record.api_enduser_username = 'unknown'

            try:
                record.api_auth_type = request_info.split('Auth:')[1].split(' Dev:')[0]
            except:
                record.api_auth_type = 'unknown'

        return True