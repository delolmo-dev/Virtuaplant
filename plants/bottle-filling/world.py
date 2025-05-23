#!/usr/bin/env python

import socket
import sys
import time      
import os
import json
import threading
import random
import pygame
from pygame.locals import *
from pygame.color import THECOLORS

import pymunk
from modbus import ServerModbus as Server, ClientModbus as Client

# PLC addresses
PLC_SERVER_IP = "localhost"
PLC_RW_ADDR = 0x0
PLC_TAG_RUN = 0x0
PLC_RO_ADDR = 0x3E8
PLC_TAG_LEVEL = 0x1
PLC_TAG_CONTACT = 0x2
PLC_TAG_MOTOR = 0x3
PLC_TAG_NOZZLE = 0x4
PLC_TAG_NEVER_STOP = 0x5

# Globals
plc = {}
motor = {}
nozzle = {}
level = {}
contact = {}
bottles = []

WORLD_SCREEN_WIDTH = 550
WORLD_SCREEN_HEIGHT = 350
FPS = 60.0

NEXT_BOTTLE_DISTANCE = 100
BOTTLE_SPACING = 60 

def to_pygame(p, scale=1.0):
    return int(p.x * scale), int((-p.y + 600) * scale)

def add_ball(space):
    mass = 0.01
    radius = 3
    inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))
    x = random.randint(181, 182)
    body = pymunk.Body(mass, inertia)
    body.position = x, 430
    shape = pymunk.Circle(body, radius, (0, 0))
    shape.collision_type = 0x6 
    space.add(body, shape)
    return shape

def draw_ball(screen, ball, scale=1.0, color=THECOLORS['blue']):
    p = to_pygame(ball.body.position, scale)
    pygame.draw.circle(screen, color, p, max(1, int(ball.radius * scale)), 2)

def add_bottle(space):
    mass = 10
    inertia = float("inf")

    body = pymunk.Body(mass, inertia)
    body.position = (130, 300)

    l1 = pymunk.Segment(body, (-150, 0), (-100, 0), 3.9)
    l2 = pymunk.Segment(body, (-150, 0), (-150, 100), 5.5)
    l3 = pymunk.Segment(body, (-100, 0), (-100, 100), 3.3)

    for l in [l1, l2, l3]:
        l.friction = 0.94
        l.elasticity = 0.5

    l1.collision_type = 0x2
    l2.collision_type = 0x3
    l3.collision_type = 0x4

    space.add(l1, l2, l3, body)
    return l1, l2, l3

def draw_lines(screen, lines, scale=1.0, color=THECOLORS['dodgerblue4']):
    for line in lines:
        body = line.body
        x = body.position.x
        if x < 130:
            alpha = max(0, (x - 100) / 30.0)  
            partial_color = (
                int(color[0] * alpha),
                int(color[1] * alpha),
                int(color[2] * alpha)
            )
        else:
            partial_color = color

        pv1 = body.position + line.a.rotated(body.angle)
        pv2 = body.position + line.b.rotated(body.angle)
        p1 = to_pygame(pv1, scale)
        p2 = to_pygame(pv2, scale)
        pygame.draw.lines(screen, partial_color, False, [p1, p2])

def add_polygon(space, pos, size, collision_type):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = pos
    shape = pymunk.Poly.create_box(body, size)
    shape.friction = 1.0
    shape.collision_type = collision_type
    space.add(body, shape)  
    return shape

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

def run_servers():
    def start_server(obj):
        if is_port_in_use(obj.port):
            print(f"the port {obj.port} is already in use. The server cannot start.")
        else:
            obj.start()

    for server in [plc['server'], motor['server'], nozzle['server'], level['server'], contact['server']]:
        threading.Thread(target=start_server, args=(server,), daemon=True).start()

def is_sensor_touching_bottle(sensor_x, sensor_y, sensor_radius, bottles):
    for bottle in bottles:
        left_segment = bottle[1]  
        body = left_segment.body

        world_a = body.position + left_segment.a.rotated(body.angle)
        world_b = body.position + left_segment.b.rotated(body.angle)

        ax, ay = to_pygame(world_a)
        bx, by = to_pygame(world_b)

        if abs(ax - bx) < 2:
            min_y = min(ay, by)
            max_y = max(ay, by)

            if abs(sensor_x - ax) <= sensor_radius and min_y <= sensor_y <= max_y:
                return True

    return False

def runWorld():
    pygame.init()
    screen = pygame.display.set_mode((WORLD_SCREEN_WIDTH, WORLD_SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("VirtuaPlant - Bottle Filling Simulation")
    clock = pygame.time.Clock()

    window_width, window_height = screen.get_size()
    scale_x = window_width / WORLD_SCREEN_WIDTH
    scale_y = window_height / WORLD_SCREEN_HEIGHT
    scale = min(scale_x, scale_y)

    space = pymunk.Space()
    space.gravity = (0.0, -900.0)

    base = add_polygon(space, (WORLD_SCREEN_WIDTH / 2, 300), (WORLD_SCREEN_WIDTH, 20), 0x7)
    nozzle_actuator = add_polygon(space, (180, 450), (15, 20), 0x9)

    bottle = add_bottle(space)
    bottles.append(bottle)
    balls = []

    sensor_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    sensor_body.position = (WORLD_SCREEN_WIDTH // 3.7, 600 - WORLD_SCREEN_HEIGHT // 1.68)

    running = True
    last_sensor_trigger_time = time.time()
    nozzle_start_time = None
    sensor_triggered = False

    while running:
        clock.tick(FPS)
        window_width, window_height = screen.get_size()
        scale_x = window_width / WORLD_SCREEN_WIDTH
        scale_y = window_height / WORLD_SCREEN_HEIGHT
        scale = min(scale_x, scale_y)
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                running = False

        fontBig = pygame.font.SysFont(None, int(40 * scale))
        fontMedium = pygame.font.SysFont(None, int(26 * scale))

        screen.fill(THECOLORS["white"])

        sensor_x = WORLD_SCREEN_WIDTH // 3.58
        sensor_y = WORLD_SCREEN_HEIGHT // 1.66
        sensor_radius = 1.5
        sensor_radius_scaled = int(sensor_radius * scale)

        tag_level = plc['level'].read(0)
        tag_contact = plc['contact'].read(0)
        tag_run = plc['server'].read(PLC_RW_ADDR + PLC_TAG_RUN)
        tag_never_stop = plc['server'].read(PLC_RW_ADDR + PLC_TAG_NEVER_STOP)
        never_stop = plc['server'].read(PLC_RW_ADDR + PLC_TAG_NEVER_STOP)

        tag_motor = 1 if tag_run == 1 and (tag_contact == 0 or tag_level == 1) else 0
        tag_nozzle = 1 if tag_run == 1 and tag_contact == 1 and tag_level == 0 else 0

        plc['motor'].write(0, tag_motor)
        plc['nozzle'].write(0, tag_nozzle)

        plc['server'].write(PLC_RO_ADDR + PLC_TAG_LEVEL, tag_level)
        plc['server'].write(PLC_RO_ADDR + PLC_TAG_CONTACT, tag_contact)
        plc['server'].write(PLC_RO_ADDR + PLC_TAG_MOTOR, tag_motor)
        plc['server'].write(PLC_RO_ADDR + PLC_TAG_NOZZLE, tag_nozzle)

        if nozzle['server'].read(0) == 1 or tag_never_stop == 2:
            if bottles:
                balls.append((add_ball(space), bottles[-1][0].body))
            else:
                balls.append((add_ball(space), None))
            last_sensor_trigger_time = time.time()


        if nozzle_start_time and (time.time() - nozzle_start_time >= 1.5):
            plc['nozzle'].write(0, 0)
            nozzle_start_time = None
            sensor_triggered = False

        if motor['server'].read(0) == 1:
            for bottle in bottles:
                body = bottle[0].body
                body.position = (body.position.x + 0.25, body.position.y)

        if tag_run == 1:
            if not bottles or (bottles[-1][0].body.position.x > 130 + BOTTLE_SPACING):
                new_bottle = add_bottle(space)
                new_bottle[0].body.position = pymunk.Vec2d(130, 300)
                bottles.append(new_bottle)

        for ball_data in balls[:]:
            ball, ball_bottle = ball_data
            if ball.body.position.y < 0 or ball.body.position.x > WORLD_SCREEN_WIDTH + 1500:
                space.remove(ball, ball.body)
                balls.remove(ball_data)
            else:
                draw_ball(screen, ball, scale)


        for bottle in bottles[:]:
            pos_x = bottle[0].body.position.x
            pos_y = bottle[0].body.position.y
            screen_pos_x = pos_x * scale
            if screen_pos_x > window_width + 1500 or pos_y < 150:

                for ball_data in balls[:]:
                    ball, ball_bottle = ball_data
                    if ball_bottle == bottle:  
                        space.remove(ball, ball.body)
                        balls.remove(ball_data)

                for segment in bottle:
                    space.remove(segment)
                space.remove(bottle[0].body)
                bottles.remove(bottle)
            else:
                draw_lines(screen, bottle, scale)

        if 'base_shape' in locals():
            space.remove(base_shape, base_shape.body)

        base_width = window_width / scale
        base_shape = add_polygon(space, (base_width / 2, 300), (base_width, 20), 0x7)

        draw_polygon(screen, base_shape, scale)

        current_time = time.time()

        if not never_stop:
            if is_sensor_touching_bottle(sensor_x, sensor_y, sensor_radius, bottles) and not sensor_triggered:
                if current_time - last_sensor_trigger_time >= 2.3:
                    sensor_triggered = True
                    plc['contact'].write(0, 1)
                    plc['nozzle'].write(0, 1)
                    nozzle_start_time = current_time
                    threading.Timer(1.8, lambda: plc['contact'].write(0, 0)).start()
                    last_sensor_trigger_time = current_time
        else:
            plc['contact'].write(0, 0)

        if not sensor_triggered:
            screen_x = int(sensor_x * scale)
            screen_y = int(sensor_y * scale)
            pygame.draw.circle(screen, THECOLORS['red'], (screen_x, screen_y), int(sensor_radius * scale))

        draw_polygon(screen, nozzle_actuator, scale)

        screen.blit(fontMedium.render("Bottle-filling factory", 1, THECOLORS['deepskyblue']), (int(10 * scale), int(10 * scale)))
        title_y = int(10 * scale)   
        screen.blit(fontMedium.render("Bottle-filling factory", 1, THECOLORS['deepskyblue']), (int(10 * scale), title_y))

        virtua_y = title_y + fontMedium.get_height() + int(4 * scale)
        screen.blit(fontBig.render("VirtuaPlant", 1, THECOLORS['gray20']), (int(10 * scale), virtua_y))

        quit_text = fontMedium.render("(press Esc to quit)", True, THECOLORS['gray70'])
        text_width = quit_text.get_width()
        screen.blit(quit_text, (window_width - text_width - int(10 * scale), int(10 * scale)))


        space.step(1 / FPS)
        pygame.display.flip()

def draw_polygon(screen, shape, scale=1.0, color=THECOLORS['black']):
    vertices = shape.get_vertices()
    points = [to_pygame(v.rotated(shape.body.angle) + shape.body.position, scale) for v in vertices]
    pygame.draw.polygon(screen, color, points)

def parse_arguments():
    try:
        ip_index = sys.argv.index("--ip") + 1
        port_index = sys.argv.index("--port") + 1

        ip = sys.argv[ip_index]
        port = int(sys.argv[port_index])

        return ip, port
    except (ValueError, IndexError):
        print("Correct Use : python3 world.py --ip <IP> --port <PORT>")
        sys.exit(1)

def main():
    global plc, motor, nozzle, level, contact

    ip, base_port = parse_arguments()

    ports = {
        "plc": base_port,
        "motor": base_port + 1,
        "nozzle": base_port + 2,
        "level": base_port + 3,
        "contact": base_port + 4
    }

    plc['server'] = Server(ip, port=ports["plc"])
    motor['server'] = Server(ip, port=ports["motor"])
    nozzle['server'] = Server(ip, port=ports["nozzle"])
    level['server'] = Server(ip, port=ports["level"])
    contact['server'] = Server(ip, port=ports["contact"])

    plc['motor'] = Client(ip, port=ports["motor"])
    plc['nozzle'] = Client(ip, port=ports["nozzle"])
    plc['level'] = Client(ip, port=ports["level"])
    plc['contact'] = Client(ip, port=ports["contact"])

    run_servers()  
    runWorld()    

if __name__ == "__main__":
    main()
