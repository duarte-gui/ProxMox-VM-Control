# vmcontrol.py
from flask import Flask, render_template, jsonify, request
import requests
import time
from gevent.pywsgi import WSGIServer

app = Flask(__name__)
    

proxmox_api_url = "https://SEUENDEREÇOEXT:8006/api2/json" # Endereço local (ip interno) 
proxmox_node = "pve" # Nome do node
vm_id_trabalho = 101  # Substitua pelo ID da sua máquina virtual de trabalho
vm_id_jogos = 100  # Substitua pelo ID da sua máquina virtual de jogos
proxmox_user = "api_access@pve!88888888-4444-4444-4444-bbbbbbbbbbbb" # Formato do usuário
proxmox_token = "88888888-4444-4444-4444-bbbbbbbbbbbb" # Formato do token após ser gerado

# Funções

def get_vm_status(vm_id):
    response = requests.get(f"{proxmox_api_url}/nodes/{proxmox_node}/qemu/{vm_id}/status/current",
                            headers={"Authorization": f"PVEAPIToken={proxmox_user}={proxmox_token}"}, verify=False)
    return response.json()['data']['status']

def start_vm(vm_id):
    # Verifique se a outra máquina está ligada
    other_vm_id = vm_id_jogos if vm_id == vm_id_trabalho else vm_id_trabalho
    other_vm_status = get_vm_status(other_vm_id)

    if other_vm_status == 'running':
        # Se a outra máquina está ligada, desligue-a primeiro
        stop_vm(other_vm_id)
        while get_vm_status(other_vm_id) != 'stopped':
            time.sleep(1)

    # Verifique se a máquina virtual atual está desligada
    current_status = get_vm_status(vm_id)
    if current_status == 'running':
        # Se a máquina já está ligada, aguarde até que seja totalmente encerrada
        stop_vm(vm_id)
        while get_vm_status(vm_id) != 'stopped':
            time.sleep(1)
        # Adicione uma pausa adicional de 3 segundos após desligar a primeira máquina
        time.sleep(3)

    # Inicie a máquina virtual
    requests.post(f"{proxmox_api_url}/nodes/{proxmox_node}/qemu/{vm_id}/status/start",
                  headers={"Authorization": f"PVEAPIToken={proxmox_user}={proxmox_token}"}, verify=False)

    # Aguarde até que a máquina esteja completamente ligada
    while get_vm_status(vm_id) != 'running':
        time.sleep(1)

    return f"Máquina virtual ({vm_id}) iniciada com sucesso!"

def stop_vm(vm_id):
    requests.post(f"{proxmox_api_url}/nodes/{proxmox_node}/qemu/{vm_id}/status/shutdown",
                  headers={"Authorization": f"PVEAPIToken={proxmox_user}={proxmox_token}"}, verify=False)
    # Aguarde até que a máquina esteja completamente desligada
    while get_vm_status(vm_id) != 'stopped':
        time.sleep(1)

# Rotas

@app.route('/')
def index():
    status_jogos = get_vm_status(vm_id_jogos)
    status_trabalho = get_vm_status(vm_id_trabalho)
    return render_template('index.html', status_jogos=status_jogos, status_trabalho=status_trabalho)

@app.route('/iniciar_jogos', methods=['POST'])
def iniciar_jogos():
    return start_vm(vm_id_jogos)

@app.route('/iniciar_trabalho', methods=['POST'])
def iniciar_trabalho():
    return start_vm(vm_id_trabalho)

@app.route('/alexa', methods=['POST'])
def alexa_endpoint():
    # Verifique se a solicitação inclui o cabeçalho 'User-Agent' da Alexa
    user_agent = request.headers.get('User-Agent')
    if 'Alexa' not in user_agent:
        return jsonify({'error': 'Acesso não autorizado'}), 403  # Retorna um erro 403 para solicitações não autorizadas

    data = request.json

    # Verifique se é uma solicitação do tipo LaunchRequest (início da skill)
    if data['request']['type'] == 'LaunchRequest':
        return jsonify({
            'version': '1.0',
            'response': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': 'Bem-vindo ao controle de máquinas virtuais. Diga "Vou jogar" ou "Vou trabalhar".'
                },
                'shouldEndSession': False
            }
        })

    # Verifique se é uma solicitação do tipo IntentRequest (intenção do usuário)
    elif data['request']['type'] == 'IntentRequest':
        intent_name = data['request']['intent']['name']

        # Processar diferentes intenções
        if intent_name == 'IniciarJogosIntent':
            start_vm(vm_id_jogos)
            return jsonify({
                'version': '1.0',
                'response': {
                    'outputSpeech': {
                        'type': 'PlainText',
                        'text': 'Vou jogar.'
                    },
                    'shouldEndSession': True
                }
            })

        elif intent_name == 'IniciarTrabalhoIntent':
            start_vm(vm_id_trabalho)
            return jsonify({
                'version': '1.0',
                'response': {
                    'outputSpeech': {
                        'type': 'PlainText',
                        'text': 'Vou trabalhar.'
                    },
                    'shouldEndSession': True
                }
            })

        # Adicione mais lógica para outras intenções, se necessário

    # Se não for uma solicitação reconhecida, retorne uma resposta padrão
    return jsonify({
        'version': '1.0',
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': 'Desculpe, não entendi essa solicitação.'
            },
            'shouldEndSession': True
        }
    })


if __name__ == '__main__':
    http_server = WSGIServer(('', 443), app)
    http_server.serve_forever()
    app.run(ssl_context=('fullchain.pem', 'privkey.pem'))

