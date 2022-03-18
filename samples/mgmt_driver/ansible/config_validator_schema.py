#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

SCHEMA = """
type: object
required:
  - vdus
properties:
  vdus:
    type: object
    additionalProperties: false
    patternProperties:
      ^[!-~]+$:
        type: object
        additionalProperties: false
        required:
          - config
        properties:
          config:
            type: object
            additionalProperties: false
            required:
              - order
              - vm_app_config
            properties:
              order:
                type: integer
              vm_app_config:
                type: object
                additionalProperties: false
                anyOf:
                  - required:
                      - instantiation
                  - required:
                      - termination
                  - required:
                      - healing
                  - required:
                      - scale-in
                  - required:
                      - scale-out
                properties:
                  type:
                    type: string
                    enum:
                      - ansible
                      - remote-command
                  node_pair:
                    type: string
                  username:
                    type: string
                  password:
                    type: string
                  priv_key_file:
                    type: string
                  retry_count:
                    type:
                      - integer
                      - string
                  retry_interval:
                    type:
                      - integer
                      - string
                  connection_wait_timeout:
                    type:
                      - integer
                      - string
                  command_execution_wait_timeout:
                    type:
                      - integer
                      - string
                  execute-host:
                    type: object
                    additionalProperties: false
                    required:
                      - host
                    properties:
                      host:
                        type: string
                      username:
                        type: string
                      password:
                        type: string
                      priv_key_file:
                        type: string
                patternProperties:
                  ^instantiation|termination|healing|scale-in|scale-out$:
                    type: array
                    items:
                      type: object
                      additionalProperties: false
                      required:
                        - order
                      oneOf:
                        - required:
                            - path
                        - required:
                            - command
                      properties:
                        path:
                          type: string
                        params:
                          type: object
                        command:
                          type: string
                        order:
                          type: integer
                        target_hosts:
                          type: array
                          items:
                            type: string
                        execute-host:
                          type: object
                          additionalProperties: false
                          required:
                            - host
                          properties:
                            host:
                              type: string
                            username:
                              type: string
                            password:
                              type: string
                            priv_key_file:
                              type: string
"""
