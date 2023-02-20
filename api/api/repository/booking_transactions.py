import json
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from api.schemas.booking_schema import BookingRequestSchema, ADMBookingRequestSchema
from models.booking_model import BookingCasesModel, BookingModel, BookingDatesModel
from models.user_model import UserModel
from models.interpreter_model import InterpreterModel
from models.booking_enums import BookingStatusEnum
from core.auth import check_user_roles



def create_booking_in_db(request:BookingRequestSchema, db: Session, username):
    
    booking_request = request.dict()
    booking_request = add_update_by(booking_request, db, username)
    booking_request['scheduling_clerk'] = booking_request['updated_by']

    booking_request['records_approved'] = False
    
    if (('interpreter_id' not in booking_request) or not booking_request['interpreter_id']):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"'interpreter_id' is required.")

    check_interpreter_contract_rules(booking_request['interpreter_id'], db, username)
    
    booking_dates = booking_request['dates']
    del booking_request['dates']

    check_conflict_dates(db, None, booking_request['interpreter_id'], booking_dates)

    new_booking = BookingModel(**booking_request)
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    add_dates(booking_dates, db, new_booking.id, new_booking.interpreter_id)
    
    return new_booking.id



def check_interpreter_contract_rules(id, db: Session, username):
    interpreter = db.query(InterpreterModel).filter(InterpreterModel.id==id).first()   
    if not interpreter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Interpreter does not exist.")

    if interpreter.contract_valid == False:
        require_roles=['cis-admin']
        check_user_roles(require_roles, username, db)



def update_booking_in_db(id: int, request:BookingRequestSchema, db: Session, username):
    booking_request = request.dict()
    booking_request = add_update_by(booking_request, db, username)
    booking_request['scheduling_clerk'] = booking_request['updated_by']

    booking_request['records_approved'] = False

    if 'interpreter_id' in booking_request:
        del booking_request['interpreter_id']

    booking_dates = booking_request['dates']
    del booking_request['dates']

    booking_query = db.query(BookingModel).filter(BookingModel.id==id)
    booking = booking_query.first()    
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking does not exist.")

    check_conflict_dates(db, booking.id, booking.interpreter_id, booking_dates)

    booking_query.update(booking_request)    
    db.commit()
    # print(booking)
    # print(booking.interpreter_id)

    add_dates(booking_dates, db, id, booking.interpreter_id)

    return booking.id



def update_adm_booking_in_db(id: int, request:ADMBookingRequestSchema, db: Session, username):
    booking_request = request.dict()
    booking_request = add_update_by(booking_request, db, username)

    if 'interpreter_id' in booking_request:
        del booking_request['interpreter_id']

    booking_request['adm_updated_by'] = booking_request['updated_by']
    if 'updated_by' in booking_request:
        del booking_request['updated_by']

    booking_dates = booking_request['dates']
    del booking_request['dates']

    booking_request['adm_detail'] = json.dumps(booking_request['adm_detail'])

    booking_query = db.query(BookingModel).filter(BookingModel.id==id)
    booking = booking_query.first()    
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking does not exist.")

    
    booking_query.update(booking_request)    
    db.commit()
    # print(booking)
    # print(booking.interpreter_id)

    add_dates(booking_dates, db, id, booking.interpreter_id)

    return booking.id



def check_conflict_dates(db:Session, booking_id, interpreter_id, booking_dates):
       
    other_booking_date_query = db.query(BookingDatesModel).join(BookingModel).filter(
        BookingDatesModel.status!=BookingStatusEnum.CANCELLED, 
        BookingDatesModel.interpreter_id==interpreter_id,
        BookingDatesModel.booking_id!=booking_id).all()
    
    current_interpreter_scheduel_date = [date.date for date in other_booking_date_query]
    
    for booking_date in booking_dates:        
        if booking_date['date'] in current_interpreter_scheduel_date and booking_date['status']!=BookingStatusEnum.CANCELLED:
            conflict_index = current_interpreter_scheduel_date.index(booking_date['date'])
            location = other_booking_date_query[conflict_index].booking.location_name
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Schedule Conflict: The interpreter is currently booked at '{location}' on '{booking_date['date'].strftime('%b %d %Y')}'.")



def add_update_by(booking_request, db: Session, username):

    current_user = db.query(UserModel).filter( UserModel.username==username).first()    
    if not current_user:
        raise HTTPException(status_code=404, detail=f"User is not available.")
        
    updated_by = current_user.display_name+"_____"+current_user.username
    booking_request['updated_by'] = updated_by
    return booking_request



def add_dates(booking_dates, db: Session, booking_id, interpreter_id):

    existing_booking_dates = db.query(BookingDatesModel).filter(BookingDatesModel.booking_id==booking_id).all()
    
    if len(existing_booking_dates)>0:
        for existing_date in existing_booking_dates:

            req_booking_date =[booking_date for booking_date in booking_dates if (('id' in booking_date) and (booking_date['id']==existing_date.id))]
            db_booking_date = db.query(BookingDatesModel).filter(BookingDatesModel.id==existing_date.id)
            
            # print(req_booking_date)
            if len(req_booking_date)>0:
                #modify
                # req_booking_date[0]['languages'] = json.dumps(req_booking_date[0]['languages'])
                booking_cases = req_booking_date[0]['cases']
                del req_booking_date[0]['cases']

                req_booking_date[0]['interpreter_id'] = interpreter_id
                req_booking_date[0]['booking_id'] = booking_id
                db_booking_date.update(req_booking_date[0])                
                add_cases(booking_cases, db, existing_date.id)
                req_booking_date[0]['processed']=True
            else:
                #delete
                db_booking_date.delete(synchronize_session=False)
        db.commit()    

    # print(booking_dates)

    for booking_date in booking_dates:

        if ('processed' in booking_date) and (booking_date['processed']==True ) :
            continue

        booking_cases = booking_date['cases']
        del booking_date['cases']
        
        del booking_date['id']
        # booking_date['languages']= json.dumps(booking_date['languages'])
        booking_date['interpreter_id'] = interpreter_id
        booking_date['booking_id'] = booking_id

        new_booking_date = BookingDatesModel(**booking_date)
        # print(new_booking_date.__dict__)
        
        db.add(new_booking_date)
        db.commit()
        db.refresh(new_booking_date)
        add_cases(booking_cases, db, new_booking_date.id)
    
    db.commit()


def add_cases(booking_cases, db: Session, booking_date_id):

    existing_booking_cases = db.query(BookingCasesModel).filter(BookingCasesModel.booking_date_id==booking_date_id).all()
    
    if len(existing_booking_cases)>0:
        for existing_case in existing_booking_cases:

            req_booking_case =[booking_case for booking_case in booking_cases if (('id' in booking_case) and (booking_case['id']==existing_case.id))]
            db_booking_case = db.query(BookingCasesModel).filter(BookingCasesModel.id==existing_case.id)
            
            # print(req_booking_date)
            if len(req_booking_case)>0:
                #modify
                # req_booking_date[0]['languages'] = json.dumps(req_booking_date[0]['languages'])
                        
                req_booking_case[0]['interpreter_language_id'] = req_booking_case[0]['language']['id']
                del req_booking_case[0]['language']

                req_booking_case[0]['booking_date_id'] = booking_date_id

                db_booking_case.update(req_booking_case[0])                                
                req_booking_case[0]['processed']=True
            else:
                #delete
                db_booking_case.delete(synchronize_session=False)
        db.commit()    

    for booking_case in booking_cases:
        # print("_______________________________-")
        # print(booking_case)

        if ('processed' in booking_case) and (booking_case['processed']==True ) :
            continue
        
        del booking_case['id']

        booking_case['interpreter_language_id'] = booking_case['language']['id']
        del booking_case['language']
        
        booking_case['booking_date_id'] = booking_date_id 

        new_booking_case = BookingCasesModel(**booking_case)
        # print(new_booking_case.__dict__)
        
        db.add(new_booking_case)
    
    db.commit()


    